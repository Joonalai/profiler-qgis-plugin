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
from typing import Any, cast

from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QEvent, QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QAbstractButton, QApplication
from qgis.utils import iface as iface_

from qgis_profiler.profiler import profiler

iface = cast(QgisInterface, iface_)

LOGGER = logging.getLogger(__name__)


class StopProfilingEvent(QEvent):
    TYPE = 300  # TODO: ensure that this is unique

    def __init__(self, name: str, group: str) -> None:
        super().__init__(QEvent(StopProfilingEvent.TYPE))
        self.name = name
        self.group = group


class ActionProfiler(QObject):
    def __init__(self, group_name: str, measure_recovery_time: bool) -> None:
        super().__init__()
        self._recording = False
        self.group = group_name
        self._measure_recovery_time = measure_recovery_time
        self._connections: dict[str, tuple[pyqtSignal, Any]] = {}

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start_recording(self) -> None:
        QApplication.instance().installEventFilter(self)
        self._recording = True

    def stop_recording(self) -> None:
        if not self._recording:
            return

        QApplication.instance().removeEventFilter(self)
        for name, (signal, connection) in self._connections.items():
            LOGGER.debug("Disconnecting action %s", name)
            try:
                signal.disconnect(connection)
            except TypeError:
                LOGGER.exception("Could not disconnect action %s", name)
        self._connections.clear()
        self._recording = False

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.MouseButtonRelease:
            widget = QApplication.widgetAt(event.globalPos())
            if widget is None or not isinstance(widget, QAbstractButton):
                return super().eventFilter(obj, event)

            # Let's go with the first action if there are any
            action = next(iter(widget.actions()), None)
            if action is not None:
                name = action.text() or action.objectName()
                if name and name not in self._connections:
                    # TODO: requires QT >= 5.13.1
                    connection = action.triggered.connect(
                        partial(self._stop_profiling_after_signal_is_emitted, name)
                    )
                    self._connections[name] = action.triggered, connection

                    self._start_profiling(name)
                    return super().eventFilter(obj, event)

            # If no suitable actions are found, connect to button.clicked
            button = cast(QAbstractButton, widget)
            name = button.text() or button.objectName()
            if name and name not in self._connections:
                connection = button.clicked.connect(
                    partial(self._stop_profiling_after_signal_is_emitted, name)
                )
                self._connections[name] = button.clicked, connection
                self._start_profiling(name)
                return super().eventFilter(obj, event)

        if event.type() == StopProfilingEvent.TYPE:
            stop_event = cast(StopProfilingEvent, event)
            LOGGER.debug("End profiling for %s", stop_event.name)
            profiler.end(
                stop_event.group,
            )
            if self._measure_recovery_time:
                profiler.profile_recovery_time(f"{stop_event.name} (recovery)")

            # Internal signal, no need to pass around
            return False

        return super().eventFilter(obj, event)

    def _start_profiling(self, name: str) -> None:
        LOGGER.debug("Start profiling for: %s", name)
        profiler.start(name, self.group)

    def _stop_profiling_after_signal_is_emitted(self, name: str) -> None:
        LOGGER.debug("Posting stop profiling event for %s", name)

        # Since event is posted, not sent, it will be delt with only after action
        # has run
        QApplication.postEvent(iface.mainWindow(), StopProfilingEvent(name, self.group))
        try:
            signal, connection = self._connections.pop(name)
            signal.disconnect(connection)
        except TypeError:
            LOGGER.exception("Could not disconnect action %s", name)
