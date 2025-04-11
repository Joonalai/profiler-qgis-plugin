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
from typing import Any, Callable, Optional

from qgis_profiler.profiler import ProfilerWrapper
from qgis_profiler.settings import (
    ProfilerSettings,
    resolve_group_name_with_cache,
)
from qgis_profiler.utils import parse_arguments

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
        if not ProfilerSettings.profiler_enabled.get_with_cache():
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
