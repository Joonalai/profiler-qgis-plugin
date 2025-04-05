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
from functools import partial
from typing import TYPE_CHECKING, Any, cast

from qgis.PyQt.QtCore import QEvent, QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QAbstractButton, QApplication
from qgis.utils import iface as iface_

from qgis_profiler import utils
from qgis_profiler.constants import QT_VERSION_MIN
from qgis_profiler.profiler import ProfilerWrapper
from qgis_profiler.utils import disconnect_signal

if TYPE_CHECKING:
    from qgis.gui import QgisInterface

iface = cast("QgisInterface", iface_)

LOGGER = logging.getLogger(__name__)


class StopProfilingEvent(QEvent):
    """Custom event to stop profiling"""

    TYPE = 313

    def __init__(self, name: str, group: str) -> None:
        super().__init__(QEvent(StopProfilingEvent.TYPE))  # type: ignore
        self.name = name
        self.group = group


class ProfilerEventRecorder(QObject):
    """
    Handles profiling events and manages signal connections.

    This class is responsible for starting and stopping profiling of various
    actions triggered within a Qt application. It utilizes event filtering
    mechanisms and connects signals to actions dynamically. Additionally, it
    supports measuring recovery times after events.

    Note: requires at least Qt version 3.13.1
    """

    event_started = pyqtSignal(str)
    event_finished = pyqtSignal(str)

    def __init__(self, group_name: str) -> None:
        super().__init__()
        self.group = group_name
        self._recording = False
        self._connections: dict[str, tuple[pyqtSignal, Any]] = {}

        if not utils.has_suitable_qt_version(QT_VERSION_MIN):
            raise ValueError(  # noqa: TRY003
                f"Qt version is too old. Please upgrade to {QT_VERSION_MIN}+"
            )

    def is_recording(self) -> bool:
        return self._recording

    def start_recording(self) -> None:
        """Starts the recording process."""
        QApplication.instance().installEventFilter(self)
        self._recording = True

    def stop_recording(self) -> None:
        """Stops the recording process."""
        if not self._recording:
            return

        QApplication.instance().removeEventFilter(self)
        if self._connections:
            for name, (signal, connection) in self._connections.items():
                LOGGER.debug("Disconnecting action %s", name)
                ProfilerWrapper.get().end(self.group)
                disconnect_signal(signal, connection, name)
        else:
            ProfilerWrapper.get().end(self.group)

        self._connections.clear()
        self._recording = False

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.MouseButtonRelease:
            if (widget := utils.get_widget_under_cursor()) is None or not isinstance(
                widget, QAbstractButton
            ):
                return super().eventFilter(obj, event)

            # If no suitable actions are found, connect to button.clicked
            button = cast("QAbstractButton", widget)
            name = button.text() or button.objectName()
            if name and name not in self._connections:
                connection = button.clicked.connect(
                    partial(self._stop_profiling_after_signal_is_emitted, name)
                )
                self._connections[name] = button.clicked, connection
                self._start_profiling(name)

        if event.type() == StopProfilingEvent.TYPE:
            stop_event = cast("StopProfilingEvent", event)
            LOGGER.debug("End profiling for %s", stop_event.name)
            ProfilerWrapper.get().end(
                stop_event.group,
            )
            self.event_finished.emit(stop_event.name)

            # Internal signal, no need to pass around
            return False

        return super().eventFilter(obj, event)

    def _start_profiling(self, name: str) -> None:
        LOGGER.debug("Start profiling for: %s", name)
        self.event_started.emit(name)
        ProfilerWrapper.get().start(name, self.group)

    def _stop_profiling_after_signal_is_emitted(self, name: str) -> None:
        LOGGER.debug("Posting stop profiling event for %s", name)

        # Since event is posted, not sent, it will be delt with only after action
        # has run
        QApplication.postEvent(iface.mainWindow(), StopProfilingEvent(name, self.group))
        signal, connection = self._connections.pop(name)
        disconnect_signal(signal, connection, name)
