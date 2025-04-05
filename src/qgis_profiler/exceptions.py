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
from qgis_plugin_tools.tools.custom_logging import bar_msg
from qgis_plugin_tools.tools.exceptions import QgsPluginException
from qgis_plugin_tools.tools.i18n import tr


class ProfilerPluginError(QgsPluginException):
    """Base class for exceptions in this module."""


class ProfilerNotFoundError(ProfilerPluginError):
    def __init__(self, item: str = "QgsApplication.profiler()") -> None:
        super().__init__(
            tr("{} not initialized", item),
            bar_msg=bar_msg(tr("File a bug report for developers")),
        )


class EventNotFoundError(ProfilerPluginError):
    def __init__(self, event_id: str, group: str) -> None:
        super().__init__(tr("{} event not found in {} group", event_id, group))


class InvalidSettingValueError(ProfilerPluginError):
    def __init__(self, setting_name: str, setting_value: str) -> None:
        super().__init__(
            tr("Invalid value for {} setting: {}", setting_name, setting_value)
        )
