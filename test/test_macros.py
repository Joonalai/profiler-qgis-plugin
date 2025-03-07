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

from typing import TYPE_CHECKING

import pytest
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QLineEdit,
    QListWidget,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from qgis_profiler.macro import (
    Macro,
    MacroKeyEvent,
    MacroMouseEvent,
    MacroMouseMoveEvent,
    MacroPlayer,
    MacroRecorder,
)

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot
    from qgis.PyQt.QtCore import QPoint

WAIT_AFTER_MOUSE_MOVE = 1


class Dialog(QDialog):
    def __init__(self, parent: object = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()

        self.button = QPushButton("Click Me")
        self.combobox = QComboBox()
        self.combobox.addItems(["Item 1", "Item 2", "Item 3"])
        self.line_edit = QLineEdit()
        self.radio_button = QRadioButton("Option 1")
        self.check_box = QCheckBox("Check Me")
        self.list_widget = QListWidget()
        self.list_widget.addItems(["List Item 1", "List Item 2", "List Item 3"])

        layout.addWidget(self.button)
        layout.addWidget(self.combobox)
        layout.addWidget(self.line_edit)
        layout.addWidget(self.radio_button)
        layout.addWidget(self.check_box)
        layout.addWidget(self.list_widget)

        self.setLayout(layout)


@pytest.fixture
def dialog(qtbot: "QtBot", qgis_parent: "QWidget") -> Dialog:
    dialog = Dialog(qgis_parent)
    qtbot.addWidget(dialog)
    dialog.show()

    # Move mouse to the dialog and simulate some mouse movements
    qtbot.mouseMove(dialog)
    qtbot.wait(WAIT_AFTER_MOUSE_MOVE)
    # qtbot.mouseMove(dialog.list_widget)
    qtbot.wait(WAIT_AFTER_MOUSE_MOVE)
    # qtbot.mouseMove(dialog.check_box)
    qtbot.wait(WAIT_AFTER_MOUSE_MOVE)
    return dialog


@pytest.fixture
def macro_recorder():
    recorder = MacroRecorder()
    recorder.start()
    return recorder


@pytest.fixture
def macro_player():
    return MacroPlayer()


@pytest.mark.xfail(reason="Ment for manual testing")
def test_macro_recorder_manual(
    macro_recorder: MacroRecorder, dialog: Dialog, qtbot: "QtBot"
):
    qtbot.wait(5000)
    macro = macro_recorder.stop()
    assert macro is None


def test_macro_recorder_button(
    macro_recorder: MacroRecorder, dialog: Dialog, qtbot: "QtBot"
):
    qtbot.mouseMove(dialog.button)
    qtbot.mousePress(dialog.button, Qt.LeftButton)
    qtbot.wait(50)
    qtbot.mousePress(dialog.button, Qt.LeftButton, Qt.KeyboardModifier.ShiftModifier)
    pos: QPoint = QCursor.pos()
    QCursor.setPos(pos.x() + 5, pos.y())
    qtbot.wait(50)
    # qtbot.mouseMove(None, QPoint(pos.x()+5, pos.y()))

    qtbot.mouseRelease(dialog.button, Qt.LeftButton)
    qtbot.wait(50)
    qtbot.mouseRelease(dialog.button, Qt.LeftButton)
    macro = macro_recorder.stop()
    assert macro is not None


def test_macro_recorder_line_edit(
    macro_recorder: MacroRecorder, dialog: Dialog, qtbot: "QtBot"
):
    qtbot.mouseMove(dialog.line_edit)
    qtbot.mousePress(dialog.line_edit, Qt.LeftButton)
    qtbot.mouseRelease(dialog.line_edit, Qt.LeftButton)
    qtbot.keyPress(dialog.line_edit, Qt.Key_A)
    qtbot.keyRelease(dialog.line_edit, Qt.Key_A)

    qtbot.wait(2000)

    macro = macro_recorder.stop()
    assert macro is not None


@pytest.mark.xfail(reason="Test is not done yet")
def test_playback(macro_player: MacroPlayer, dialog: Dialog, qtbot: "QtBot"):
    qtbot.wait(1000)
    macro = Macro(
        events=[
            MacroMouseMoveEvent(
                ms_since_last_event=0, modifiers=0, buttons=0, positions=[(3269, 327)]
            ),
            MacroKeyEvent(
                ms_since_last_event=134, key=16777250, is_release=True, modifiers=0
            ),
            MacroMouseMoveEvent(
                ms_since_last_event=0,
                modifiers=0,
                buttons=0,
                positions=[(3267, 326), (3212, 246)],
            ),
            MacroMouseEvent(
                ms_since_last_event=59,
                position=(3212, 246),
                is_release=False,
                button=1,
                modifiers=0,
            ),
            MacroMouseEvent(
                ms_since_last_event=92,
                position=(3212, 246),
                is_release=True,
                button=1,
                modifiers=0,
            ),
            MacroKeyEvent(ms_since_last_event=0, key=70, is_release=False, modifiers=0),
            MacroKeyEvent(
                ms_since_last_event=114, key=70, is_release=True, modifiers=0
            ),
            MacroKeyEvent(ms_since_last_event=0, key=79, is_release=False, modifiers=0),
            MacroKeyEvent(ms_since_last_event=79, key=79, is_release=True, modifiers=0),
            MacroKeyEvent(ms_since_last_event=0, key=79, is_release=False, modifiers=0),
            MacroKeyEvent(ms_since_last_event=79, key=79, is_release=True, modifiers=0),
            MacroKeyEvent(ms_since_last_event=0, key=32, is_release=False, modifiers=0),
            MacroKeyEvent(
                ms_since_last_event=120, key=32, is_release=True, modifiers=0
            ),
            MacroKeyEvent(ms_since_last_event=0, key=66, is_release=False, modifiers=0),
            MacroKeyEvent(ms_since_last_event=99, key=66, is_release=True, modifiers=0),
            MacroKeyEvent(
                ms_since_last_event=0, key=16777219, is_release=False, modifiers=0
            ),
            MacroKeyEvent(
                ms_since_last_event=39, key=16777219, is_release=True, modifiers=0
            ),
            MacroKeyEvent(
                ms_since_last_event=0,
                key=16777248,
                is_release=False,
                modifiers=33554432,
            ),
            MacroKeyEvent(
                ms_since_last_event=0, key=66, is_release=False, modifiers=33554432
            ),
            MacroKeyEvent(
                ms_since_last_event=79, key=66, is_release=True, modifiers=33554432
            ),
            MacroKeyEvent(
                ms_since_last_event=0, key=65, is_release=False, modifiers=33554432
            ),
            MacroKeyEvent(
                ms_since_last_event=0, key=82, is_release=False, modifiers=33554432
            ),
            MacroKeyEvent(
                ms_since_last_event=78, key=65, is_release=True, modifiers=33554432
            ),
            MacroKeyEvent(
                ms_since_last_event=19, key=82, is_release=True, modifiers=33554432
            ),
            MacroKeyEvent(
                ms_since_last_event=19, key=16777248, is_release=True, modifiers=0
            ),
            MacroMouseMoveEvent(
                ms_since_last_event=0, modifiers=0, buttons=0, positions=[(3211, 246)]
            ),
        ],
        name=None,
        speed=1.0,
    )
    macro_player.play(macro)
    qtbot.wait(5000)
    assert dialog.line_edit.text() == "foo bar"
