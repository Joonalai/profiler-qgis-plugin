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

import dataclasses
import time

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QEvent, QObject, QPoint, pyqtSignal
from qgis.PyQt.QtWidgets import QWidget

from qgis_profiler.profiler import ProfilerResult


@dataclasses.dataclass
class WidgetInfo:
    """Helper class for macro tests."""

    name: str
    widget: QWidget
    x: int
    y: int

    @property
    def local_center(self) -> QPoint:
        return QPoint(self.x, self.y)

    @property
    def global_point(self) -> QPoint:
        return self.widget.mapToGlobal(QPoint(self.x, self.y))

    @property
    def global_xy(self) -> tuple[int, int]:
        point = self.global_point
        return point.x(), point.y()

    @staticmethod
    def from_widget(name: str, widget: QWidget) -> "WidgetInfo":
        center = widget.geometry().center()
        return WidgetInfo(name, widget, center.x(), center.y())


def wait(wait_ms: int) -> None:
    """Wait for a given number of milliseconds."""
    t = time.time()
    while time.time() - t < wait_ms / 1000:
        QgsApplication.processEvents()


def profiler_data_with_group(
    group: str, profile_data: list[ProfilerResult]
) -> list[ProfilerResult]:
    """Set group for all profiler results."""
    return [
        ProfilerResult(
            result.name,
            group,
            result.duration,
            profiler_data_with_group(group, result.children),
        )
        for result in profile_data
    ]


class WidgetEventListener(QObject):
    double_clicked = pyqtSignal()  # Signal emitted when a double click is detected.

    def __init__(self) -> None:
        super().__init__(None)
        self.widgets: list[QWidget] = []

    def start_listening(self, widget: QWidget) -> None:
        widget.installEventFilter(self)
        self.widgets.append(widget)

    def stop_listening(self) -> None:
        for widget in self.widgets:
            widget.removeEventFilter(self)
        self.widgets.clear()

    def eventFilter(self, watched_object: QObject, event: QEvent):  # noqa: N802
        """Override of QObject.eventFilter to detect double clicks."""
        if event.type() == QEvent.MouseButtonDblClick:
            self.double_clicked.emit()
        return super().eventFilter(watched_object, event)
