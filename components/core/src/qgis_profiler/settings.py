#  Copyright (c) 2025-2026 profiler-qgis-plugin contributors.
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
import logging
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis_plugin_tools.tools.i18n import tr
from qgis_plugin_tools.tools.resources import profile_path
from qgis_plugin_tools.tools.settings import (
    get_setting,
    set_setting,
)

from qgis_profiler.constants import CACHE_INTERVAL
from qgis_profiler.exceptions import InvalidSettingValueError

LOGGER = logging.getLogger(__name__)


class WidgetType(enum.Enum):
    LINE_EDIT = "line_edit"
    CHECKBOX = "checkbox"
    SPIN_BOX = "spin_box"


class SettingCategory(enum.Enum):
    GENERAL = tr("General")
    PROFILER_GROUPS = tr("Profiler Groups")
    CPROFILER = tr("cProfiler")
    RECOVERY_METER = tr("Recovery Meter")
    THREAD_HEALTH_CHECKER_METER = tr("Thread Health Meter")
    MAP_RENDERING_METER = tr("Map Rendering Meter")


@dataclass
class WidgetConfig:
    """Configuration options for different widget types."""

    minimum: int | float | None = None
    maximum: int | float | None = None
    step: int | float | None = None


@dataclass
class Setting(QObject):
    description: str
    default: Any
    category: SettingCategory = SettingCategory.GENERAL
    widget_config: WidgetConfig | None = None
    widget_type: WidgetType | None = None
    changed = pyqtSignal()

    def __post_init__(self) -> None:
        """Deduces the widget type based on the default value's type."""
        super().__init__()
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


class Settings(enum.Enum):
    """
    Represents the Profiler Settings, designed for managing configuration
    of the profiler plugin via QgsSettings. Use get and set methods to
    interact with the settings.

    This class provides a structured way to access, and manage
    profiler-related settings.
    """

    # General settings
    profiler_enabled = Setting(
        description=tr("Enable profiling"),
        default=True,
        category=SettingCategory.GENERAL,
    )
    show_events_threshold = Setting(
        description=tr("Hide events shorter than this (seconds)"),
        default=0.01,
        category=SettingCategory.GENERAL,
    )
    start_recording_on_startup = Setting(
        description=tr("Automatically start recording when QGIS launches"),
        default=False,
        category=SettingCategory.GENERAL,
    )

    # Profiler group settings (advanced)
    active_group = Setting(
        description=tr("Group name for plugin profiling results"),
        default=tr("Profiler"),
        category=SettingCategory.PROFILER_GROUPS,
    )
    recorded_group = Setting(
        description=tr("Group name for recorded event results"),
        default=tr("Profiler"),
        category=SettingCategory.PROFILER_GROUPS,
    )
    meters_group = Setting(
        description=tr("Group name for meter measurement results"),
        default=tr("Profiler"),
        category=SettingCategory.PROFILER_GROUPS,
    )
    cprofiler_profile_path = Setting(
        description=tr("File path for saving cProfile reports"),
        default=profile_path("profiler", "cprofiler_report.prof"),
        category=SettingCategory.CPROFILER,
    )
    cprofiler_log_line_count = Setting(
        description=tr("Maximum number of lines in cProfile report"),
        default=100,
        category=SettingCategory.CPROFILER,
    )

    # Recovery meter settings
    recovery_meter_enabled = Setting(
        description=tr("Enable recovery meter"),
        default=True,
        category=SettingCategory.RECOVERY_METER,
    )
    recovery_threshold = Setting(
        description=tr("Expected recovery time (seconds)"),
        default=0.8,
        widget_config=WidgetConfig(minimum=0.0, maximum=100.0, step=0.1),
        category=SettingCategory.RECOVERY_METER,
    )
    recovery_timeout = Setting(
        description=tr("Timeout before giving up (seconds)"),
        default=10,
        category=SettingCategory.RECOVERY_METER,
    )
    recovery_process_event_count = Setting(
        description=tr("Number of events to process per measurement"),
        default=100000,
        widget_config=WidgetConfig(minimum=1, maximum=1000000, step=10),
        category=SettingCategory.RECOVERY_METER,
    )

    # Thread health checker meter settings
    thread_health_checker_enabled = Setting(
        description=tr("Enable thread health checker"),
        default=True,
        category=SettingCategory.THREAD_HEALTH_CHECKER_METER,
    )
    thread_health_checker_poll_interval = Setting(
        description=tr("Time between health checks (seconds)"),
        default=1.0,
        category=SettingCategory.THREAD_HEALTH_CHECKER_METER,
    )
    thread_health_checker_threshold = Setting(
        description=tr("Expected main thread response time (seconds)"),
        default=0.1,
        category=SettingCategory.THREAD_HEALTH_CHECKER_METER,
        widget_config=WidgetConfig(minimum=0.001, maximum=100.0, step=0.001),
    )

    # Map rendering meter settings
    map_rendering_meter_enabled = Setting(
        description=tr("Enable map rendering meter"),
        default=True,
        category=SettingCategory.MAP_RENDERING_METER,
    )
    map_rendering_meter_threshold = Setting(
        description=tr("Expected map render time (seconds)"),
        default=1.0,
        category=SettingCategory.MAP_RENDERING_METER,
    )

    @staticmethod
    def reset() -> None:
        """
        Resets the state of the application or relevant subsystem to its initial default
        state.
        """
        for setting in Settings:
            setting.set(setting.value.default)

    def get(self) -> Any:
        """Gets the setting value."""
        setting = self.value
        value = get_setting(self.name, setting.default)
        if not isinstance(value, type(setting.default)):
            if isinstance(self.value.default, bool) and isinstance(value, str):
                value = value.lower() == "true"
            else:
                value = type(setting.default)(value)
        if self == Settings.profiler_enabled:
            return os.environ.get("QGIS_PROFILER_ENABLED", value)
        return value

    def get_with_cache(self) -> Any:
        """Gets the setting value with caching."""
        time_hash = int(time.time() / CACHE_INTERVAL)
        return self._get_cached(time_hash)

    def set(self, value: Any) -> None:
        """Sets the setting value."""
        if not isinstance(value, type(self.value.default)):
            if isinstance(self.value.default, bool):
                value = bool(value)
            else:
                raise InvalidSettingValueError(self.name, value)
        set_setting(self.name, value)
        self.value.changed.emit()

    @lru_cache
    def _get_cached(self, time_hash: int) -> Any:
        """
        This method uses a time-sensitive hash to ensure
        that cache stays valid maximum of CACHE_INTERVAL seconds.
        """
        return self.get()


def resolve_group_name(group: str | None = None) -> str:
    """Helper method to resolve the group name, falling back to settings."""
    if group is not None:
        return group
    return Settings.active_group.get()


def resolve_group_name_with_cache(group: str | None = None) -> str:
    """Helper method to resolve the group name with cache, falling back to settings."""
    if group is not None:
        return group
    return Settings.active_group.get_with_cache()
