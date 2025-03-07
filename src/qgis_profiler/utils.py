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
from typing import Optional

from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtWidgets import QApplication, QWidget

from qgis_profiler.settings import ProfilerSettings


def resolve_group_name(group: Optional[str] = None, use_cache: bool = True) -> str:
    """Helper method to resolve the group name, falling back to settings."""
    if group is not None:
        return group
    if use_cache:
        return ProfilerSettings.active_group.get_with_cache()
    return ProfilerSettings.active_group.get()


def get_widget_under_cursor() -> Optional[QWidget]:
    """Ensure the widget under the mouse cursor gets focus."""
    widget = QApplication.widgetAt(QCursor.pos())
    if widget:
        widget.setFocus()
    return widget
