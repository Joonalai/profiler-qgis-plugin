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
import enum
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from qgis_plugin_tools.tools.i18n import tr
from qgis_plugin_tools.tools.settings import (
    get_setting,
    set_setting,
)

from qgis_profiler.constants import CACHE_INTERVAL


@dataclass
class Setting:
    description: str
    default: Any
    category: str = "Profiling"


class ProfilerSettings(enum.Enum):
    """
    Represents the Profiler Settings, designed for managing configuration
    of the profiler plugin via QgsSettings. Use get and set methods to
    interact with the settings.

    This class provides a structured way to access, and manage
    profiler-related settings.
    """

    # Profiler settings
    active_group = Setting(
        tr("A profiling group used with plugin profiling"), tr("Plugins")
    )
    recorded_group = Setting(
        tr("A profiling group used with recorded event profiling"),
        tr("Recorded Events"),
    )
    recovery_group = Setting(
        tr("A profiling group used with recovery profiling"), tr("Recovery")
    )
    profiler_enabled = Setting(
        tr("Is profiling enabled when using profiling decorations"), True
    )
    normal_time = Setting(
        tr("A time in seconds it normally takes to run recovery test"), 0.8
    )  # TODO: add calibration method
    timeout = Setting(
        tr("A timeout in seconds after recovery measurement should exit"), 20
    )
    process_event_count = Setting(
        tr("Number of process events call in recovery measurement"), 100000
    )
    measure_recovery_when_recording = Setting(
        tr("Measure recovery profiling with recorded event profiling"), True
    )

    @staticmethod
    def reset() -> None:
        """
        Resets the state of the application or relevant subsystem to its initial default
        state.
        """
        for setting in ProfilerSettings:
            setting.set(setting.value.default)

    def get(self) -> Any:
        """Gets the setting value."""
        setting = self.value
        value = type(setting.default)(get_setting(self.name, setting.default))
        if self == ProfilerSettings.profiler_enabled:
            return os.environ.get("QGIS_PROFILER_ENABLED", value)
        return value

    def get_with_cache(self) -> Any:
        """Gets the setting value with caching."""
        time_hash = int(time.time() / CACHE_INTERVAL)
        return self._get_cached(time_hash)

    def set(self, value: Any) -> bool:
        """Sets the setting value."""
        return set_setting(self.name, value)

    @lru_cache
    def _get_cached(self, time_hash: int) -> Any:
        """
        This method uses time sensitive hash to ensure
        that cache stays valid maximum of CACHE_INTERVAL seconds.
        """
        return self.get()
