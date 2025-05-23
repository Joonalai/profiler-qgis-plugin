#  Copyright (c) 2025 profiler-qgis-plugin contributors.
#
#
#  This file is part of profiler-qgis-plugin.
#
#  profiler-qgis-plugin is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  profiler-qgis-plugin is distributed in the hope that it will be
#  useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#  of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with profiler-qgis-plugin. If not, see <https://www.gnu.org/licenses/>.
import logging
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional

from qgis_profiler.profiler import ProfilerWrapper
from qgis_profiler.settings import (
    Settings,
    resolve_group_name_with_cache,
)
from qgis_profiler.utils import QgisPluginType, get_rotated_path, parse_arguments

LOGGER = logging.getLogger(__name__)


def profile(
    function: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    group: Optional[str] = None,
    event_args: Optional[list[str]] = None,
) -> Callable:
    """
    Creates a profiling decorator that measures the time taken by a function and groups
    the profiler data under a specified name. The decorator utilizes the
    QgsApplication's profiling infrastructure for performance measurement.

    :param function: Provided here to support both @monitor and @monitor() syntax.
    :param name: Optional name for the profiler item. If not provided, the function's
        name will be used as the name.
    :param group: Optional name for the profiler group. If not provided, the group name
    is read from settings.
    :param event_args: Optional list of argument names to include in the event name.
        If specified, the event name will include these argument values.
    :return: A decorator that wraps the specified function for profiling.
    """

    if function is None:  # @profile() syntax

        def decorator(function: Callable) -> Callable:
            return profile(
                function=function,
                name=name,
                group=group,
                event_args=event_args,
            )

        return decorator

    # @profile syntax
    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not Settings.profiler_enabled.get_with_cache():
            LOGGER.debug("Profiling is disabled.")
            return function(*args, **kwargs)

        group_name = resolve_group_name_with_cache(group)
        event_name = name if name is not None else function.__name__
        if event_args:
            event_name += parse_arguments(function, event_args, args, kwargs)

        ProfilerWrapper.get().start(event_name, group_name)
        try:
            return function(*args, **kwargs)
        finally:
            ProfilerWrapper.get().end(group_name)

    # Mark wrapper as profiled
    wrapper._profiled = True  # type: ignore
    return wrapper


def profile_class(  # noqa: C901
    *,
    group: Optional[str] = None,
    include: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
) -> Callable[[type], type]:
    """
    A class decorator to automatically wrap methods with the 'profile' decorator.
    If 'profile' decorator is already applied to a method, it will be skipped.

    :param group: Optional name for the profiler group. If not provided, the group name
    is read from settings.
    :param include: List of method names to include
    (only these will be wrapped if provided).
    :param exclude: List of method names to exclude
    (these will NOT be wrapped, overrides include).
    :return: A class with decorated methods based on the include/exclude criteria.
    """

    def decorator(cls: type) -> type:  # noqa: C901
        for attr_name, attr_value in cls.__dict__.items():
            # Ignore special methods (__ methods)
            if attr_name.startswith("__"):
                continue

            # Apply wrapping rules based on include/exclude
            if include and attr_name not in include:
                continue  # Skip methods not in the "include" list
            if exclude and attr_name in exclude:
                continue  # Skip methods in the "exclude" list

            # Handle staticmethod and classmethod separately
            is_static = isinstance(attr_value, staticmethod)
            is_class_method = isinstance(attr_value, classmethod)
            is_method = callable(attr_value)

            if is_static or is_class_method:
                original_func = attr_value.__func__
            elif is_method:
                original_func = attr_value
            else:
                continue

            # Omit if method is already decorated with profiler
            if hasattr(original_func, "_profiled"):
                continue

            wrapper = profile(name=attr_name, group=group)

            if is_static:
                # Unwrap staticmethod before decorating
                wrapped_func = wrapper(original_func)
                setattr(cls, attr_name, staticmethod(wrapped_func))
            elif is_class_method:
                # Unwrap classmethod before decorating
                wrapped_func = wrapper(original_func)
                setattr(cls, attr_name, classmethod(wrapped_func))
            # Check if the attribute is a callable (method)
            elif is_method:
                # Wrap the method with @profile
                setattr(cls, attr_name, wrapper(original_func))
        return cls

    return decorator


def cprofile(
    function: Optional[Callable] = None,
    *,
    log_stats: bool = True,
    trim_zeros: bool = True,
    sort: tuple[str, ...] = ("cumtime",),
    output_file_path: Optional[Path] = None,
) -> Callable:
    """
    Profiles the execution of a specified function using cProfile. Can be used
    as a decorator with or without arguments.

    :param function: Function to be profiled. Defaults to None.
    :param log_stats: Whether to log profiling statistics. Defaults to True.
    :param trim_zeros: Trim lines with zero times from the report.
    :param sort: Tuple of columns used for sorting profiling output.
    :param output_file_path: File path to save profiling output, if provided.
    :return: Callable decorator or wrapped function.
    """
    if function is None:  # @cprofile() syntax

        def decorator(function: Callable) -> Callable:
            return cprofile(
                function=function,
                log_stats=log_stats,
                sort=sort,
                output_file_path=output_file_path,
            )

        return decorator

    # @cprofile syntax
    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not Settings.profiler_enabled.get():
            LOGGER.debug("Profiling is disabled.")
            return function(*args, **kwargs)

        ProfilerWrapper.get().cprofiler.enable()
        try:
            return function(*args, **kwargs)
        finally:
            ProfilerWrapper.get().cprofiler.disable()
            if log_stats:
                report = ProfilerWrapper.get().cprofiler.get_stat_report(
                    sort=sort, trim_zeros=trim_zeros
                )
                LOGGER.info(report)
            if output_file_path:
                ProfilerWrapper.get().cprofiler.dump_stats(output_file_path)

    return wrapper


def cprofile_plugin(
    *,
    output_file_path: Path,
) -> Callable[[type], type]:
    """
    Apply a decorator to a QGIS plugin class to enable profiling.

    This function decorates a class to integrate profiling functionality
    via `cProfile`. Profiling is enabled during the plugin's execution
    and additional profiling statistics are logged after the plugin
    unloads.

    The output file can then be further analysed for example with tools like

    https://github.com/jrfonseca/gprof2dot
    and
    https://jiffyclub.github.io/snakeviz/#snakeviz

    :param output_file_path: Path to save profiling results.
    If the file exists, a suffix will be added to the filename.
    :return: Decorated class.
    """

    def decorator(cls: type) -> type:
        if not Settings.profiler_enabled.get():
            LOGGER.debug("Profiling is disabled.")
            return cls

        if not issubclass(cls, QgisPluginType):
            raise TypeError(f"Class {cls.__name__} is not a QGIS plugin")  # noqa: TRY003

        original_unload = cls.unload

        @wraps(original_unload)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return original_unload(*args, **kwargs)
            finally:
                output_file_path.parent.mkdir(parents=True, exist_ok=True)
                path = get_rotated_path(output_file_path)
                LOGGER.info(
                    "Stopping cprofiler for the plugin %s and saving results to %s",
                    cls.__name__,
                    path,
                )
                ProfilerWrapper.get().cprofiler.dump_stats(path)

        setattr(cls, "unload", wrapper)  # noqa: B010
        LOGGER.info("Starting cprofiler for the plugin %s", cls.__name__)
        ProfilerWrapper.get().cprofiler.enable()
        return cls

    return decorator
