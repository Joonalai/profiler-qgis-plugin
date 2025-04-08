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
from typing import Any, Callable, Optional

from qgis_profiler.meters.recovery_measurer import RecoveryMeasurer
from qgis_profiler.profiler import ProfilerWrapper
from qgis_profiler.settings import (
    ProfilerSettings,
    resolve_group_name_with_cache,
)

LOGGER = logging.getLogger(__name__)


def profile(
    *,
    name: Optional[str] = None,
    group: Optional[str] = None,
    event_args: Optional[list[str]] = None,
) -> Callable:
    """
    Creates a profiling decorator that measures the time taken by a function and groups
    the profiler data under a specified name. The decorator utilizes the
    QgsApplication's profiling infrastructure for performance measurement.

    :param name: Optional name for the profiler item. If not provided, the function's
        name will be used as the name.
    :param group: Optional name for the profiler group. If not provided, the group name
    is read from settings.
    :param event_args: Optional list of argument names to include in the event name.
        If specified, the event name will include these argument values.
    :return: A decorator that wraps the specified function for profiling.
    """

    def profiling_wrapper(function: Callable) -> Callable:
        from functools import wraps

        @wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not ProfilerSettings.profiler_enabled.get_with_cache():
                LOGGER.debug("Profiling is disabled.")
                return function(*args, **kwargs)

            group_name = resolve_group_name_with_cache(group)
            event_name = name if name is not None else function.__name__
            if event_args:
                event_name += _parse_arguments(function, event_args, args, kwargs)

            ProfilerWrapper.get().start(event_name, group_name)
            try:
                return function(*args, **kwargs)
            finally:
                ProfilerWrapper.get().end(group_name)

        return wrapper

    return profiling_wrapper


def profile_class(
    *,
    group: Optional[str] = None,
    include: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
) -> Callable[[type], type]:
    """
    A class decorator to automatically wrap methods with the 'profile' decorator.

    :param group: Optional name for the profiler group. If not provided, the group name
    is read from settings.
    :param include: List of method names to include
    (only these will be wrapped if provided).
    :param exclude: List of method names to exclude
    (these will NOT be wrapped, overrides include).
    :return: A class with decorated methods based on the include/exclude criteria.
    """

    def decorator(cls: type) -> type:
        for attr_name, attr_value in cls.__dict__.items():
            # Ignore special methods (__ methods)
            if attr_name.startswith("__"):
                continue

            # Apply wrapping rules based on include/exclude
            if include and attr_name not in include:
                continue  # Skip methods not in the "include" list
            if exclude and attr_name in exclude:
                continue  # Skip methods in the "exclude" list

            wrapper = profile(name=attr_name, group=group)

            # Handle staticmethod and classmethod separately
            if isinstance(attr_value, staticmethod):
                # Unwrap staticmethod before decorating
                original_func = attr_value.__func__
                wrapped_func = wrapper(original_func)
                setattr(cls, attr_name, staticmethod(wrapped_func))
            elif isinstance(attr_value, classmethod):
                # Unwrap classmethod before decorating
                original_func = attr_value.__func__
                wrapped_func = wrapper(original_func)
                setattr(cls, attr_name, classmethod(wrapped_func))
            # Check if the attribute is a callable (method)
            elif callable(attr_value):
                # Wrap the method with @profile
                setattr(cls, attr_name, wrapper(attr_value))
        return cls

    return decorator


def profile_recovery_time(
    *,
    name: Optional[str] = None,
    group: Optional[str] = None,
    event_args: Optional[list[str]] = None,
) -> Callable:
    """
    Profiles the recovery time of a function execution and records it using a specified
    profiler. The recovery time is measured after the function execution completes,
    even if it raises an exception. The recovered time measurement data is grouped
    under a specified group and tagged with an event name for categorization.

    :param name: Optional event name for this profiling. If not provided, the
        name of the function being wrapped will be used.
    :param group: Optional group name under which this profiling record will
        be categorized in the profiler.
    :param event_args: Optional list of argument names to include in the event name.
        If specified, the event name will include these argument values.
    :return: A callable decorator function that wraps the given function to
        measure and profile its recovery time.
    """

    def profile_recovery_time_wrapper(function: Callable) -> Callable:
        from functools import wraps

        @wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not ProfilerSettings.profiler_enabled.get_with_cache():
                LOGGER.debug("Profiling is disabled.")
                return function(*args, **kwargs)

            group_name = resolve_group_name_with_cache(group)
            event_name = name if name is not None else function.__name__
            if event_args:
                event_name += _parse_arguments(function, event_args, args, kwargs)

            try:
                return function(*args, **kwargs)
            finally:
                meter = RecoveryMeasurer.get()
                with meter.context(event_name) as context:
                    duration = meter.measure()
                # Meter might not be enabled
                if duration is not None:
                    ProfilerWrapper.get().add_record(context, group_name, duration)
                else:
                    LOGGER.debug("Recovery time measurement is disabled.")

        return wrapper

    return profile_recovery_time_wrapper


def _parse_arguments(
    function: Callable, event_args: list[str], args: Any, kwargs: Any
) -> str:
    """
    Parse argument value from the function specified
    """
    arg_names = function.__code__.co_varnames[: function.__code__.co_argcount]
    arg_dict = {**dict(zip(arg_names, args)), **kwargs}
    arg_values = [
        f"{event_arg}={arg_dict[event_arg]}"
        for event_arg in event_args
        if event_arg in arg_dict
    ]
    return f"({', '.join(arg_values)})"
