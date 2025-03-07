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

from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest
from qgis.PyQt.QtCore import Qt

from qgis_profiler.macro import (
    Macro,
    MacroKeyEvent,
    MacroMouseDoubleClickEvent,
    MacroMouseEvent,
    MacroMouseMoveEvent,
    MacroPlayer,
    MacroRecorder,
)
from test.conftest import Dialog
from test.utils import WidgetEventListener, WidgetInfo

WAIT_MS = 5

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


@pytest.fixture
def macro_recorder() -> Iterator[MacroRecorder]:
    recorder = MacroRecorder()
    recorder.start_recording()
    yield recorder
    recorder.stop_recording()


@pytest.fixture
def macro_player():
    return MacroPlayer()


@pytest.fixture
def widget_listener() -> Iterator[WidgetEventListener]:
    listener = WidgetEventListener()
    try:
        yield listener
    finally:
        listener.stop_listening()


@pytest.mark.skip(reason="Ment for manual testing")
def test_macro_recorder_manual(
    macro_recorder: MacroRecorder, dialog: Dialog, qtbot: "QtBot"
):
    qtbot.wait(5000)
    macro = macro_recorder.stop_recording()
    assert macro is None


@pytest.mark.parametrize(
    "modifier",
    [
        Qt.NoModifier,
        Qt.ShiftModifier,
        Qt.ControlModifier,
        Qt.AltModifier,
        Qt.KeyboardModifiers(Qt.ControlModifier | Qt.AltModifier),
    ],
    ids=[
        "no_modifier",
        "shift_modifier",
        "control_modifier",
        "alt_modifier",
        "control_alt_modifier",
    ],
)
def test_macro_recorder_should_record_button_clicking_macro(
    dialog: Dialog,
    macro_recorder: MacroRecorder,
    dialog_widget_positions: dict[str, WidgetInfo],
    qtbot: "QtBot",
    modifier: Qt.KeyboardModifier,
):
    # Arrange
    button = dialog_widget_positions["button"]

    # Act
    qtbot.mouseClick(
        dialog.button, Qt.LeftButton, pos=button.local_center, modifier=modifier
    )
    macro = macro_recorder.stop_recording()

    # Assert
    assert macro == Macro(
        events=[
            MacroMouseEvent(
                position=button.global_xy,
                modifiers=int(modifier),
            ),
            MacroMouseEvent(
                position=button.global_xy,
                is_release=True,
                modifiers=int(modifier),
            ),
        ],
        name=None,
        speed=1.0,
    )


@pytest.mark.parametrize(
    "modifier",
    [
        Qt.NoModifier,
        Qt.ShiftModifier,
        Qt.ControlModifier,
        Qt.AltModifier,
        Qt.KeyboardModifiers(Qt.ControlModifier | Qt.AltModifier),
    ],
    ids=[
        "no_modifier",
        "shift_modifier",
        "control_modifier",
        "alt_modifier",
        "control_alt_modifier",
    ],
)
def test_macro_recorder_should_record_button_double_clicking_macro(
    dialog: Dialog,
    macro_recorder: MacroRecorder,
    dialog_widget_positions: dict[str, WidgetInfo],
    qtbot: "QtBot",
    modifier: Qt.KeyboardModifier,
):
    # Arrange
    button = dialog_widget_positions["button"]

    # Act
    qtbot.mouseDClick(
        dialog.button, Qt.LeftButton, pos=button.local_center, modifier=modifier
    )
    macro = macro_recorder.stop_recording()

    # Assert
    assert macro == Macro(
        events=[
            MacroMouseDoubleClickEvent(
                position=button.global_xy,
                button=1,
                modifiers=int(modifier),
            ),
        ],
        name=None,
        speed=1.0,
    )


@pytest.mark.parametrize(
    "modifier",
    [
        Qt.NoModifier,
        Qt.ShiftModifier,
        Qt.ControlModifier,
        Qt.AltModifier,
        Qt.KeyboardModifiers(Qt.ControlModifier | Qt.AltModifier),
    ],
    ids=[
        "no_modifier",
        "shift_modifier",
        "control_modifier",
        "alt_modifier",
        "control_alt_modifier",
    ],
)
@pytest.mark.xfail(reason="Modifiers do not work properly yet")
def test_macro_recorder_should_record_key_clicking_macro(
    dialog: Dialog,
    macro_recorder: MacroRecorder,
    dialog_widget_positions: dict[str, WidgetInfo],
    qtbot: "QtBot",
    modifier: Qt.KeyboardModifier,
):
    # Arrange
    line_edit = dialog_widget_positions["line_edit"]

    # Act
    qtbot.wait(WAIT_MS)
    qtbot.mouseMove(dialog.line_edit, pos=line_edit.local_center)
    qtbot.wait(WAIT_MS * 5)
    qtbot.mouseClick(dialog.line_edit, Qt.LeftButton, pos=line_edit.local_center)
    qtbot.keyPress(dialog.line_edit, Qt.Key_A, modifier=modifier)
    qtbot.wait(WAIT_MS)
    qtbot.keyRelease(dialog.line_edit, Qt.Key_A, modifier=modifier)
    macro = macro_recorder.stop_recording()

    assert (
        dialog.line_edit.text() == "a"
        if modifier | Qt.ShiftModifier != modifier
        else "A"
    )

    # Assert
    assert macro == Macro(
        events=[
            MacroMouseMoveEvent(positions=[line_edit.global_xy]),
            MacroMouseEvent(
                position=line_edit.global_xy,
            ),
            MacroMouseEvent(
                position=line_edit.global_xy,
                is_release=True,
            ),
            MacroKeyEvent(
                key=Qt.Key_A,
                modifiers=int(modifier),
            ),
            MacroKeyEvent(
                key=Qt.Key_A,
                modifiers=int(modifier),
                is_release=True,
            ),
        ],
        name=None,
        speed=1.0,
    )


def test_macro_player_play_button_macro(
    macro_recorder: MacroRecorder,
    macro_player: MacroPlayer,
    dialog_widget_positions: dict[str, WidgetInfo],
    dialog: Dialog,
    qtbot: "QtBot",
):
    # Arrange
    qtbot.mouseMove(dialog.button)
    qtbot.wait(WAIT_MS * 5)
    qtbot.mouseClick(dialog.button, Qt.LeftButton)
    macro = macro_recorder.stop_recording()

    # Act and assert
    with qtbot.waitSignal(dialog.button.clicked, timeout=10):
        macro_player.play(macro)


def test_macro_player_play_button_double_click_macro(
    macro_recorder: MacroRecorder,
    macro_player: MacroPlayer,
    dialog_widget_positions: dict[str, WidgetInfo],
    dialog: Dialog,
    widget_listener: WidgetEventListener,
    qtbot: "QtBot",
):
    # Arrange
    qtbot.mouseMove(dialog.button)
    qtbot.mouseDClick(dialog.button, Qt.LeftButton)
    macro = macro_recorder.stop_recording()
    widget_listener.start_listening(dialog.button)

    # Act and assert
    with qtbot.waitSignal(widget_listener.double_clicked, timeout=10):
        macro_player.play(macro)


def test_macro_player_play_line_edit_macro(
    macro_recorder: MacroRecorder,
    macro_player: MacroPlayer,
    dialog_widget_positions: dict[str, WidgetInfo],
    dialog: Dialog,
    widget_listener: WidgetEventListener,
    qtbot: "QtBot",
):
    # Arrange
    qtbot.mouseMove(dialog.line_edit)
    qtbot.mouseClick(dialog.line_edit, Qt.LeftButton)
    qtbot.keyClick(dialog.line_edit, Qt.Key_A)
    macro = macro_recorder.stop_recording()
    dialog.line_edit.clear()

    # Act and assert
    with qtbot.waitSignal(dialog.line_edit.textEdited, timeout=5000):
        macro_player.play(macro)
    assert dialog.line_edit.text() == "a"
