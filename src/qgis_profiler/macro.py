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
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QElapsedTimer, QEvent, QObject, QPoint, Qt
from qgis.PyQt.QtGui import QCursor, QKeyEvent, QMouseEvent
from qgis.PyQt.QtTest import QTest
from qgis.PyQt.QtWidgets import QApplication, QWidget

from qgis_profiler import utils
from qgis_profiler.constants import MS_EPSILON

LOGGER = logging.getLogger(__name__)


@dataclass
class MacroEvent(ABC):
    ms_since_last_event: int = 0

    @abstractmethod
    def perform_event_action(self) -> None: ...

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MacroEvent):
            return NotImplemented

        # If difference is
        return abs(self.ms_since_last_event - other.ms_since_last_event) < MS_EPSILON


@dataclass
class MacroKeyEvent(MacroEvent):
    key: int = 0
    is_release: bool = False
    modifiers: int = Qt.NoModifier

    def perform_event_action(self) -> None:
        widget = QApplication.focusWidget()
        QgsApplication.processEvents()
        # TODO: shift is not working
        if not self.is_release:
            QTest.keyPress(
                widget, Qt.Key(self.key), Qt.KeyboardModifiers(self.modifiers)
            )
        else:
            QTest.keyRelease(
                widget, Qt.Key(self.key), Qt.KeyboardModifiers(self.modifiers)
            )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MacroKeyEvent):
            return NotImplemented
        return super().__eq__(other) and (
            self.ms_since_last_event == other.ms_since_last_event
            and self.key == other.key
            and self.is_release == other.is_release
            and self.modifiers == other.modifiers
        )


@dataclass
class MacroMouseMoveEvent(MacroEvent):
    positions: list[tuple[int, int]] = field(default_factory=list)
    buttons: int = Qt.NoButton
    modifiers: int = Qt.NoModifier

    def add_position(self, position: tuple[int, int]) -> None:
        if self.positions and position == self.positions[-1]:
            return
        self.positions.append(position)

    def perform_event_action(self) -> None:
        if self.buttons != Qt.NoButton:
            return self.perform_event_action_with_event()

        for position in self.positions:
            QCursor.setPos(*position)
            QgsApplication.processEvents()
        return None

    def perform_event_action_with_event(self) -> None:
        for position in self.positions:
            global_pos = QPoint(*position)
            widget = QApplication.widgetAt(global_pos)
            local_pos = widget.mapFromGlobal(global_pos) if widget else global_pos
            # Create and send mouse move events
            event = QMouseEvent(
                QEvent.MouseMove,
                local_pos,
                global_pos,
                Qt.NoButton,
                Qt.MouseButtons(self.buttons),
                Qt.KeyboardModifiers(self.modifiers),
            )
            QApplication.postEvent(widget, event)
            QApplication.processEvents()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MacroMouseMoveEvent):
            return NotImplemented
        return super().__eq__(other) and (
            self.positions == other.positions
            and self.buttons == other.buttons
            and self.modifiers == other.modifiers
        )

    def __repr__(self) -> str:
        if len(self.positions) == 1:
            positions = self.positions
        else:
            positions = [self.positions[0], self.positions[-1]]
        return (
            f"MacroMouseMoveEvent(ms_since_last_event={self.ms_since_last_event}, "
            f"modifiers={self.modifiers}, "
            f"buttons={self.buttons}, "
            f"positions={positions})"
        )


@dataclass
class MacroMouseEvent(MacroEvent):
    position: tuple[int, int] = (0, 0)
    is_release: bool = False
    button: int = Qt.LeftButton
    modifiers: int = Qt.NoModifier

    def perform_event_action(self) -> None:
        position = QPoint(*self.position)
        widget = utils.get_widget_under_cursor()
        if not widget:
            return
        widget.setFocus()
        position = widget.mapFromGlobal(position)
        if not self.is_release:
            # Ensure the widget under the mouse cursor is focused
            QTest.mousePress(
                widget,
                Qt.MouseButton(self.button),
                Qt.KeyboardModifiers(self.modifiers),
                position,
            )
        else:
            QTest.mouseRelease(
                widget,
                Qt.MouseButton(self.button),
                Qt.KeyboardModifiers(self.modifiers),
                position,
            )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MacroMouseEvent):
            return NotImplemented
        return super().__eq__(other) and (
            self.position == other.position
            and self.button == other.button
            and self.modifiers == other.modifiers
            and self.is_release == other.is_release
        )


@dataclass
class MacroMouseDoubleClickEvent(MacroEvent):
    position: tuple[int, int] = (0, 0)
    button: int = Qt.LeftButton
    modifiers: int = Qt.NoModifier

    def perform_event_action(self) -> None:
        position = QPoint(*self.position)
        widget = utils.get_widget_under_cursor()
        if widget:
            widget.setFocus()
            position = widget.mapFromGlobal(position)
        QTest.mouseDClick(
            widget,
            Qt.MouseButton(self.button),
            Qt.KeyboardModifiers(self.modifiers),
            position,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MacroMouseDoubleClickEvent):
            return NotImplemented
        return super().__eq__(other) and (
            self.position == other.position
            and self.button == other.button
            and self.modifiers == other.modifiers
        )


@dataclass
class Macro:
    events: list[MacroEvent]
    name: Optional[str] = None
    speed: float = 1.0


class MacroRecorder(QObject):
    """
    Manages recording of user actions like mouse and keyboard events.

    Tracks and collects events during a recording session, allowing
    filtered or unfiltered playback of these events for automation.
    """

    def __init__(
        self,
        filter_out_mouse_movements: bool = True,  # noqa: FBT001, FBT002
    ) -> None:
        super().__init__(None)
        self._recorded_events: list[MacroEvent] = []
        self._timer = QElapsedTimer()
        self.last_record_time = 0  # Tracks the last timestamp
        self._recording = False
        self._filter_out_mouse_movements = filter_out_mouse_movements
        self._widgets_to_filter_events_out: list[QWidget] = []

    def add_widget_to_filter_events_out(self, widget: QWidget) -> None:
        """Add a widget to filter events out from the recorded events."""
        self._widgets_to_filter_events_out.append(widget)

    def is_recording(self) -> bool:
        """Check if the recorder is currently recording."""
        return self._recording

    def start_recording(self) -> None:
        """Start recording user actions."""
        self._recorded_events.clear()
        self._recording = True
        self._timer.restart()
        QApplication.instance().installEventFilter(self)

    def stop_recording(self) -> Macro:
        """
        Stop recording user actions.

        :return: New Macro object with recorded events
        """
        self._recording = False
        QApplication.instance().removeEventFilter(self)
        events = (
            self._get_filtered_events()
            if self._filter_out_mouse_movements
            else self._recorded_events
        )
        LOGGER.debug(events)
        return Macro(events)

    def eventFilter(self, watched_object: QObject, event: QEvent) -> bool:  # noqa: N802
        """Event filter to record keyboard and mouse events."""
        if not self._recording:
            return super().eventFilter(watched_object, event)

        elapsed = self._timer.elapsed()
        ms_since_last_event = elapsed - self.last_record_time
        self.last_record_time = elapsed

        if (
            isinstance(event, QMouseEvent)
            and QApplication.widgetAt(event.globalPos())
            in self._widgets_to_filter_events_out
        ):
            return super().eventFilter(watched_object, event)

        # TODO: mouse wheel
        if event.type() in [QEvent.KeyPress, QEvent.KeyRelease]:
            self._record_key_event(event, ms_since_last_event)
        elif event.type() in [QEvent.MouseButtonPress, QEvent.MouseButtonRelease]:
            self._record_mouse_button_event(event, ms_since_last_event)
        elif event.type() == QEvent.MouseButtonDblClick:
            self._record_mouse_button_double_click_event(event, ms_since_last_event)
        elif event.type() == QEvent.MouseMove:
            self._record_mouse_move_event(event)

        return super().eventFilter(watched_object, event)

    def _get_filtered_events(self) -> list[MacroEvent]:
        filtered_events: list[MacroEvent] = []

        if not self._recorded_events:
            return []

        # Take just the last mouse position
        first_element = self._recorded_events[0]
        if isinstance(first_element, MacroMouseMoveEvent):
            first_index = 1
            filtered_events.append(
                MacroMouseMoveEvent(0, [first_element.positions[-1]])
            )
        else:
            first_index = 0

        # TODO: filter out last events, ie. stopping the recording
        filtered_events.extend(self._recorded_events[first_index:])

        return filtered_events

    def _record_key_event(self, event: QKeyEvent, elapsed: int) -> None:
        """Record key press or release events."""
        macro_event = MacroKeyEvent(
            elapsed,
            key=event.key(),
            is_release=event.type() == QEvent.KeyRelease,
            modifiers=int(event.modifiers()),
        )

        # Do not add if the last mouse button event was the same
        for i in range(len(self._recorded_events) - 1, -1, -1):
            if isinstance((previous_event := self._recorded_events[i]), MacroKeyEvent):
                if (
                    previous_event.key == macro_event.key
                    and previous_event.is_release == macro_event.is_release
                ):
                    return
                break

        self._recorded_events.append(macro_event)

    def _record_mouse_button_event(self, event: QMouseEvent, elapsed: int) -> None:
        """Record mouse button press or release events."""
        macro_event = MacroMouseEvent(
            elapsed,
            position=(event.globalX(), event.globalY()),
            is_release=event.type() == QEvent.MouseButtonRelease,
            button=event.button(),
            modifiers=int(event.modifiers()),
        )

        # Do not add if the last mouse button event was the same
        for i in range(len(self._recorded_events) - 1, -1, -1):
            if isinstance(
                (previous_event := self._recorded_events[i]), MacroMouseEvent
            ):
                if (
                    previous_event.button == macro_event.button
                    and previous_event.is_release == macro_event.is_release
                ):
                    return
                break

        self._recorded_events.append(macro_event)

    def _record_mouse_button_double_click_event(
        self, event: QMouseEvent, elapsed: int
    ) -> None:
        """Record mouse double click events."""
        self._recorded_events.append(
            MacroMouseDoubleClickEvent(
                ms_since_last_event=elapsed,
                position=(event.globalX(), event.globalY()),
                button=event.button(),
                modifiers=int(event.modifiers()),
            )
        )

    def _record_mouse_move_event(self, event: QMouseEvent) -> None:
        """Record mouse movement events."""
        current_position = (event.globalX(), event.globalY())
        last_event = self._recorded_events[-1] if self._recorded_events else None
        if isinstance(last_event, MacroMouseMoveEvent):
            last_event.add_position(current_position)
        else:
            self._recorded_events.append(
                MacroMouseMoveEvent(
                    0,
                    positions=[current_position],
                    buttons=int(event.buttons()),
                    modifiers=int(event.modifiers()),
                )
            )


class MacroPlayer:
    """
    Represents an object used for macro playback with adjustable speed.

    Used to execute a sequence of predefined events at a specified playback speed.
    """

    def __init__(self, playback_speed: float = 1.0) -> None:
        """
        Represents an object used for macro playback with adjustable speed.

        :param playback_speed: Playback speed factor.
        """
        self._speed = playback_speed
        self._timer = QElapsedTimer()

    def play(self, macro: Macro) -> None:
        """Play back the recorded events."""
        playback_speed = self._speed * macro.speed
        for event in macro.events:
            self._timer.restart()
            while self._timer.elapsed() < event.ms_since_last_event * playback_speed:
                QgsApplication.processEvents()
            QgsApplication.processEvents()
            # TODO: if widget is not inside QGIS, QGIS might crash
            event.perform_event_action()
