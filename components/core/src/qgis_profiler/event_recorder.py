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

"""Records UI events such as button clicks and map tool interactions for profiling.

Contains :class:`ProfilerEventRecorder`, which installs a Qt event filter to
automatically capture and time user-triggered actions in QGIS.
"""

import logging
from functools import partial
from typing import TYPE_CHECKING, Any, cast

from qgis.gui import QgsMapTool
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import QEvent, QObject, QPoint, Qt, pyqtBoundSignal, pyqtSignal
from qgis.PyQt.QtGui import QMouseEvent
from qgis.PyQt.QtWidgets import QApplication, QStyle, QStyleOptionButton
from qgis.utils import iface as iface_
from qgis_plugin_tools.utils.typing_utils import require

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
        """Initialize with profiling event name and group."""
        super().__init__(self.EVENT_TYPE)
        self.name = name
        self.group = group


class ProfilerEventRecorder(QObject):
    """Handles profiling events and manages signal connections.

    This class is responsible for starting and stopping profiling of various
    actions triggered within a Qt application. It utilizes event filtering
    mechanisms and connects signals to actions dynamically.

    Example::

        from qgis_profiler.event_recorder import ProfilerEventRecorder

        recorder = ProfilerEventRecorder(group_name="User Interactions")

        # Connect to signals for custom handling
        recorder.event_started.connect(lambda name: print(f"Started: {name}"))
        recorder.event_finished.connect(lambda name: print(f"Finished: {name}"))

        recorder.start_recording()
        # ... user interacts with QGIS ...
        recorder.stop_recording()
    """

    # TODO: menu buttons...  # noqa: TD003

    event_started = pyqtSignal(str)
    event_finished = pyqtSignal(str)

    def __init__(
        self,
        group_name: str,
        map_tools_config: dict[str, CustomEventConfig] | None = None,
        general_map_tools_config: list[CustomEventConfig] | None = None,
    ) -> None:
        """Initialize with group name and optional map tool configurations."""
        super().__init__()
        self.group = group_name
        self._map_tools_config = map_tools_config or DEFAULT_MAP_TOOLS_CONFIG
        self._general_map_tools_config = (
            general_map_tools_config or GENERAL_MAP_TOOL_FUNCTIONALITIES
        )
        self._recording = False
        self._connections: dict[str, tuple[pyqtBoundSignal, Any]] = {}
        # Started but not yet stopped profiler events as (name, event id)
        # pairs in start order. Stops are matched to starts by name so that
        # a stop for one event can never end some other event.
        self._started_events: list[tuple[str, str]] = []
        self._current_map_tool_config: CustomEventConfig | None = None

        if not utils.has_suitable_qt_version(QT_VERSION_MIN):
            msg = f"Qt version is too old. Please upgrade to {QT_VERSION_MIN}+"
            raise ValueError(msg)

    def is_recording(self) -> bool:
        """Return whether event recording is currently active."""
        return self._recording

    def start_recording(self) -> None:
        """Start the recording process."""
        require(QApplication.instance()).installEventFilter(self)
        canvas = require(iface.mapCanvas())
        canvas.mapToolSet.connect(self._map_tool_changed)
        self._map_tool_changed(canvas.mapTool(), None)
        self._recording = True

    def stop_recording(self) -> None:
        """Stop the recording process."""
        if not self._recording:
            return

        require(QApplication.instance()).removeEventFilter(self)
        if self._connections:
            for name, (signal, connection) in self._connections.items():
                LOGGER.debug("Disconnecting action %s", name)
                disconnect_signal(signal, connection, name)

        disconnect_signal(
            require(iface.mapCanvas()).mapToolSet,
            self._map_tool_changed,
            "map_tool_set",
        )

        self._end_all_events()
        self._connections.clear()
        self._recording = False

    def eventFilter(  # noqa: N802  # ty: ignore[invalid-method-override]
        self, obj: QObject | None, event: QEvent | None
    ) -> bool:
        """Filter Qt events for profiling button clicks and map tool actions."""
        if obj is None or event is None:
            return False

        self._catch_button_events(obj, event)
        self._catch_map_tool_events(obj, event)

        if event.type() == StopProfilingEvent.EVENT_TYPE:
            stop_event = cast("StopProfilingEvent", event)
            self._stop_profiling(stop_event.name, stop_event.group)

            # Internal signal, no need to pass around
            return False

        return super().eventFilter(obj, event)

    def _catch_button_events(self, obj: QObject, event: QEvent) -> None:
        if event.type() != QEvent.Type.MouseButtonRelease or not isinstance(
            obj, QtWidgets.QAbstractButton
        ):
            return

        # Profiling is stopped when the button emits clicked. Start only if the
        # release is going to emit it, otherwise the event would never be
        # stopped and it would accumulate the time of every later event.
        button = obj
        if not _release_emits_clicked(button, cast("QMouseEvent", event)):
            return

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

        if config is None:
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

    def _map_tool_changed(
        self, current: QgsMapTool | None, _: QgsMapTool | None
    ) -> None:
        self._end_all_events()
        if current is not None and (
            config := self._map_tools_config.get(current.__class__.__name__)
        ):
            LOGGER.debug("Map tool changed to %s", config.class_name)
            self._current_map_tool_config = config
            config.activate()
        else:
            LOGGER.debug("Map tool changed to unknown tool")
            self._current_map_tool_config = None

    def _start_profiling(self, name: str) -> None:
        LOGGER.debug("Start profiling: %s", name)
        self.event_started.emit(name)
        event_id = ProfilerWrapper.get().start(name, self.group)
        self._started_events.append((name, event_id))

    def _stop_profiling(self, name: str, group: str) -> None:
        index = next(
            (
                i
                for i in reversed(range(len(self._started_events)))
                if self._started_events[i][0] == name
            ),
            None,
        )
        if index is None:
            LOGGER.debug("Ignoring stop for %s which is not running", name)
            return
        if not ProfilerWrapper.get().end_event(self._started_events[index][1], group):
            del self._started_events[index]
            return
        # The profiler can only end the most recent event, so ending this
        # event also ended the events started after it (nested events).
        # Finish them too, most recent first, so that every started event
        # is finished exactly once.
        ended_events = self._started_events[index:]
        del self._started_events[index:]
        for ended_name, _ in reversed(ended_events):
            LOGGER.debug("Stop profiling: %s", ended_name)
            self.event_finished.emit(ended_name)

    def _end_all_events(self) -> None:
        ProfilerWrapper.get().end_all(self.group)
        self._started_events.clear()

    def _stop_profiling_after_signal_is_emitted(self, name: str) -> None:
        LOGGER.debug("Posting stop profiling event for %s", name)

        self._post_stop_profiling_event(name)
        signal, connection = self._connections.pop(name)
        disconnect_signal(signal, connection, name)

    def _post_stop_profiling_event(self, name: str) -> None:
        """Post a stop-profiling event to be handled after UI becomes responsive.

        :param name: Name of the profiling event.
        """
        QApplication.postEvent(
            require(iface.mainWindow()), StopProfilingEvent(name, self.group)
        )


def _release_emits_clicked(
    button: QtWidgets.QAbstractButton, event: QMouseEvent
) -> bool:
    """Return whether the mouse release will make the button emit clicked.

    Mirror the conditions of QAbstractButton.mouseReleaseEvent: the left
    button is released while the button is down (it was pressed) and the
    cursor is still over the clickable area of the button.
    """
    if event.button() != Qt.MouseButton.LeftButton or not button.isDown():
        return False
    position = event.position().toPoint() if hasattr(event, "position") else event.pos()
    return _hit_button(button, position)


def _hit_button(button: QtWidgets.QAbstractButton, position: QPoint) -> bool:
    """Mirror QAbstractButton.hitButton, which is protected and thus not callable.

    QCheckBox and QRadioButton override it to accept only releases over the
    indicator and the label, not over the rest of the widget.
    """
    if isinstance(button, QtWidgets.QCheckBox):
        click_rect = QStyle.SubElement.SE_CheckBoxClickRect
    elif isinstance(button, QtWidgets.QRadioButton):
        click_rect = QStyle.SubElement.SE_RadioButtonClickRect
    else:
        return button.rect().contains(position)

    option = QStyleOptionButton()
    option.initFrom(button)
    option.text = button.text()
    option.icon = button.icon()
    option.iconSize = button.iconSize()
    return button.style().subElementRect(click_rect, option, button).contains(position)
