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
from typing import TYPE_CHECKING, Any, Optional, cast

from qgis.gui import QgsMapTool
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import QEvent, QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QApplication
from qgis.utils import iface as iface_

from qgis_profiler import utils
from qgis_profiler.config.event_config import (
    DEFAULT_MAP_TOOLS_CONFIG,
    GENERAL_MAP_TOOL_FUNCTIONALITIES,
    CustomEventConfig,
    EventResponse,
)
from qgis_profiler.constants import QT_VERSION_MIN
from qgis_profiler.profiler import ProfilerWrapper
from qgis_profiler.utils import disconnect_signal

if TYPE_CHECKING:
    from qgis.gui import QgisInterface

iface = cast("QgisInterface", iface_)

LOGGER = logging.getLogger(__name__)


class StopProfilingEvent(QEvent):
    """Custom event to stop the profiling for a specific action."""

    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, name: str, group: str) -> None:
        super().__init__(self.EVENT_TYPE)  # type: ignore
        self.name = name
        self.group = group


class ProfilerEventRecorder(QObject):
    """
    Handles profiling events and manages signal connections.

    This class is responsible for starting and stopping profiling of various
    actions triggered within a Qt application. It utilizes event filtering
    mechanisms and connects signals to actions dynamically.

    Note: requires at least Qt version 3.13.1
    """

    # TODO: menu buttons...

    event_started = pyqtSignal(str)
    event_finished = pyqtSignal(str)

    def __init__(
        self,
        group_name: str,
        map_tools_config: Optional[dict[str, CustomEventConfig]] = None,
        general_map_tools_config: Optional[list[CustomEventConfig]] = None,
    ) -> None:
        super().__init__()
        self.group = group_name
        self._map_tools_config = map_tools_config or DEFAULT_MAP_TOOLS_CONFIG
        self._general_map_tools_config = (
            general_map_tools_config or GENERAL_MAP_TOOL_FUNCTIONALITIES
        )
        self._recording = False
        self._connections: dict[str, tuple[pyqtSignal, Any]] = {}
        self._current_map_tool_config: Optional[CustomEventConfig] = None

        if not utils.has_suitable_qt_version(QT_VERSION_MIN):
            raise ValueError(  # noqa: TRY003
                f"Qt version is too old. Please upgrade to {QT_VERSION_MIN}+"
            )

    def is_recording(self) -> bool:
        return self._recording

    def start_recording(self) -> None:
        """Starts the recording process."""
        QApplication.instance().installEventFilter(self)
        iface.mapCanvas().mapToolSet.connect(self._map_tool_changed)
        self._map_tool_changed(iface.mapCanvas().mapTool(), None)
        self._recording = True

    def stop_recording(self) -> None:
        """Stops the recording process."""
        if not self._recording:
            return

        QApplication.instance().removeEventFilter(self)
        if self._connections:
            for name, (signal, connection) in self._connections.items():
                LOGGER.debug("Disconnecting action %s", name)
                disconnect_signal(signal, connection, name)

        disconnect_signal(
            iface.mapCanvas().mapToolSet, self._map_tool_changed, "map_tool_set"
        )

        ProfilerWrapper.get().end_all(self.group)
        self._connections.clear()
        self._recording = False

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        self._catch_button_events(event)
        self._catch_map_tool_events(obj, event)

        if event.type() == StopProfilingEvent.EVENT_TYPE:
            stop_event = cast("StopProfilingEvent", event)
            self._stop_profiling(stop_event.name, stop_event.group)

            # Internal signal, no need to pass around
            return False

        return super().eventFilter(obj, event)

    def _catch_button_events(self, event: QEvent) -> None:
        if event.type() == QEvent.MouseButtonRelease:
            if (widget := utils.get_widget_under_cursor()) is None or not isinstance(
                widget, QtWidgets.QAbstractButton
            ):
                return

            # If no suitable actions are found, connect to button.clicked
            button = cast("QtWidgets.QAbstractButton", widget)
            name = button.text() or button.objectName()
            if name and name not in self._connections:
                connection = button.clicked.connect(
                    partial(self._stop_profiling_after_signal_is_emitted, name)
                )
                self._connections[name] = button.clicked, connection
                self._start_profiling(name)

    def _catch_map_tool_events(self, obj: QObject, event: QEvent) -> None:
        response = None
        if (config := self._current_map_tool_config) is None or not (
            response := config.matches(event, obj)
        ):
            # If no suitable event found, try general map tool configs
            # (e.g., zoom with wheel, pan with middle button)
            for config in self._general_map_tools_config:
                if (response := config.matches(event, obj)) is not None:
                    break
            if response is None:
                return

        if response == EventResponse.START_PROFILING:
            self._start_profiling(config.name)
        elif response == EventResponse.STOP_PROFILING:
            self._stop_profiling(config.name, self.group)
        elif response == EventResponse.STOP_PROFILING_DELAYED:
            self._post_stop_profiling_event(config.name)
        elif response == EventResponse.START_AND_STOP_DELAYED:
            self._start_profiling(config.name)
            self._post_stop_profiling_event(config.name)

    def _map_tool_changed(self, current: QgsMapTool, _: Optional[QgsMapTool]) -> None:
        ProfilerWrapper.get().end_all(self.group)
        if config := self._map_tools_config.get(current.__class__.__name__):
            LOGGER.debug("Map tool changed to %s", config.class_name)
            self._current_map_tool_config = config
            config.activate()
        else:
            LOGGER.debug("Map tool changed to unknown tool")
            self._current_map_tool_config = None

    def _start_profiling(self, name: str) -> None:
        LOGGER.debug("Start profiling: %s", name)
        self.event_started.emit(name)
        ProfilerWrapper.get().start(name, self.group)

    def _stop_profiling(self, name: str, group: str) -> None:
        LOGGER.debug("Stop profiling: %s", name)
        ProfilerWrapper.get().end(group)
        self.event_finished.emit(name)

    def _stop_profiling_after_signal_is_emitted(self, name: str) -> None:
        LOGGER.debug("Posting stop profiling event for %s", name)

        self._post_stop_profiling_event(name)
        signal, connection = self._connections.pop(name)
        disconnect_signal(signal, connection, name)

    def _post_stop_profiling_event(self, name: str) -> None:
        """
        Since event is posted, not sent, it will be delt with
        only after action has run or UI becomes responsive.
        :param name: Name of the profiling event.
        """
        QApplication.postEvent(iface.mainWindow(), StopProfilingEvent(name, self.group))
