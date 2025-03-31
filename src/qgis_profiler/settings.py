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
from typing import Any, Optional, Union

from qgis_plugin_tools.tools.i18n import tr
from qgis_plugin_tools.tools.settings import (
    get_setting,
    set_setting,
)

from qgis_profiler.constants import CACHE_INTERVAL
from qgis_profiler.exceptions import InvalidSettingValueError


class WidgetType(enum.Enum):
    LINE_EDIT = "line_edit"
    CHECKBOX = "checkbox"
    SPIN_BOX = "spin_box"


@dataclass
class WidgetConfig:
    """Configuration options for different widget types."""

    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    step: Optional[Union[int, float]] = None


@dataclass
class Setting:
    description: str
    default: Any
    category: str = tr("Profiling")
    widget_config: Optional[WidgetConfig] = None
    widget_type: Optional[WidgetType] = None

    def __post_init__(self) -> None:
        """Deduces the widget type based on the default value's type."""
        if isinstance(self.default, bool):
            self.widget_type = WidgetType.CHECKBOX
        elif isinstance(self.default, (int, float)):
            self.widget_type = WidgetType.SPIN_BOX
            # Provide default widget configuration for numeric inputs if not set
            if self.widget_config is None:
                self.widget_config = WidgetConfig(
                    minimum=0,
                    maximum=100,
                    step=1 if isinstance(self.default, int) else 0.1,
                )
        elif isinstance(self.default, str):
            self.widget_type = WidgetType.LINE_EDIT
        else:
            raise NotImplementedError


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
        description=tr("A profiling group used with plugin profiling"),
        default=tr("Plugins"),
    )
    recorded_group = Setting(
        description=("A profiling group used with recorded event profiling"),
        default=("Recorded Events"),
    )
    meters_group = Setting(
        description=("A profiling group used with various meters"),
        default=("Meters"),
    )
    profiler_enabled = Setting(
        description=("Is profiling enabled"),
        default=True,
    )
    normal_time = Setting(
        description=("A time in seconds it normally takes to run recovery test"),
        default=0.8,
        widget_config=WidgetConfig(minimum=0.0, maximum=100.0, step=0.1),
    )  # TODO: add calibration method
    timeout = Setting(
        description=("A timeout in seconds after recovery measurement should exit"),
        default=20,
    )
    process_event_count = Setting(
        description=("Number of process events call in recovery measurement"),
        default=100000,
        widget_config=WidgetConfig(minimum=1, maximum=1000000, step=10),
    )
    measure_recovery_when_recording = Setting(
        description=("Measure recovery profiling with recorded event profiling"),
        default=True,
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
        if not isinstance(value, type(self.value.default)):
            if isinstance(self.value.default, bool):
                value = bool(value)
            else:
                raise InvalidSettingValueError(self.name, value)
        return set_setting(self.name, value)

    @lru_cache
    def _get_cached(self, time_hash: int) -> Any:
        """
        This method uses time sensitive hash to ensure
        that cache stays valid maximum of CACHE_INTERVAL seconds.
        """
        return self.get()


def resolve_group_name(group: Optional[str] = None) -> str:
    """Helper method to resolve the group name, falling back to settings."""
    if group is not None:
        return group
    return ProfilerSettings.active_group.get()


def resolve_group_name_with_cache(group: Optional[str] = None) -> str:
    """Helper method to resolve the group name with cache, falling back to settings."""
    if group is not None:
        return group
    return ProfilerSettings.active_group.get_with_cache()
