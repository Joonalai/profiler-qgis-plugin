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

from qgis_plugin_tools.tools.i18n import tr

from qgis_profiler.profiler import ProfilerWrapper
from qgis_profiler.settings import (
    ProfilerSettings,
    resolve_group_name_with_cache,
)

LOGGER = logging.getLogger(__name__)


def profile(*, name: Optional[str] = None, group: Optional[str] = None) -> Callable:
    """
    Creates a profiling decorator that measures the time taken by a function and groups
    the profiler data under a specified name. The decorator utilizes the
    QgsApplication's profiling infrastructure for performance measurement.

    :param name: Optional name for the profiler item. If not provided, the function's
        name will be used as the name.
    :param group: Optional name for the profiler group. If not provided, the group name
    is read from settings.
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
            ProfilerWrapper.get().start(event_name, group_name)
            try:
                return function(*args, **kwargs)
            finally:
                ProfilerWrapper.get().end(group_name)

        return wrapper

    return profiling_wrapper


def profile_recovery_time(
    *, name: Optional[str] = None, group: Optional[str] = None
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

            event_name = name if name is not None else function.__name__
            event_name += f" {tr('(recovery)')}"
            try:
                return function(*args, **kwargs)
            finally:
                ProfilerWrapper.get().profile_recovery_time(event_name, group)

        return wrapper

    return profile_recovery_time_wrapper
