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
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

import pytest
from qgis.PyQt.QtCore import QModelIndex, Qt
from qgis.PyQt.QtWidgets import QInputDialog, QToolButton

from profiler_plugin.ui.macro.macro_model import MacroTableModel
from profiler_plugin.ui.macro.macro_panel import MacroPanel
from qgis_profiler.macro import Macro, MacroPlayer, MacroRecorder

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from pytest_subtests import SubTests
    from pytestqt.qtbot import QtBot

MACRO_NAME = "Test macro"


@pytest.fixture
def mock_macro(mocker: "MockerFixture") -> MagicMock:
    mock_macro = mocker.create_autospec(Macro, instance=True)
    mock_macro.name = MACRO_NAME
    return mock_macro


@pytest.fixture
def mock_macro_recorder(
    mocker: "MockerFixture", mock_macro: "MagicMock"
) -> "MagicMock":
    mock_macro_recorder = mocker.create_autospec(MacroRecorder, instance=True)
    mock_macro_recorder.is_recording = (
        lambda: mock_macro_recorder.start_recording.call_count
        > mock_macro_recorder.stop_recording.call_count
    )
    mock_macro_recorder.stop_recording.return_value = mock_macro
    return mock_macro_recorder


@pytest.fixture
def mock_macro_player(mocker: "MockerFixture", mock_macro: "MagicMock") -> "MagicMock":
    return mocker.create_autospec(MacroPlayer, instance=True)


@pytest.fixture
def mock_input_dialog(mocker: "MockerFixture") -> "MagicMock":
    return mocker.patch.object(QInputDialog, "getText", return_value=(MACRO_NAME, True))


@pytest.fixture
def macro_panel(
    mock_macro_recorder: "MagicMock",
    mock_macro_player: "MagicMock",
    qtbot: "QtBot",
    mock_input_dialog: "MagicMock",
    mock_profiler: "MagicMock",
) -> MacroPanel:
    panel = MacroPanel(mock_macro_recorder, mock_macro_player)
    panel.setFixedSize(200, 300)
    qtbot.addWidget(panel)
    panel.show()
    return panel


@pytest.fixture
def macro_model(macro_panel: MacroPanel) -> MacroTableModel:
    model = macro_panel.table_view.model()
    assert model is not None
    return cast(MacroTableModel, model)


@pytest.fixture
def mock_index(mocker: "MockerFixture") -> "MagicMock":
    mock_index = mocker.create_autospec(QModelIndex)
    mock_index.isValid.return_value = False
    return mock_index


@pytest.fixture
def record_macro(macro_panel: MacroPanel, qtbot: "QtBot") -> None:
    qtbot.mouseClick(macro_panel.button_record, Qt.LeftButton)
    qtbot.mouseClick(macro_panel.button_record, Qt.LeftButton)


@pytest.fixture
def set_macro_selected(macro_panel: MacroPanel) -> None:
    macro_panel.table_view.selectRow(0)


def test_macro_panel_initialization(
    macro_panel: MacroPanel,
    macro_model: MacroTableModel,
    mock_index: "MagicMock",
    mock_macro_recorder: MagicMock,
) -> None:
    assert macro_panel.button_record.isEnabled()
    assert not macro_panel.button_record.isChecked()
    assert not macro_panel.button_play.isEnabled()
    assert not macro_panel.button_delete.isChecked()
    assert not macro_model.macros

    # All buttons should have icons and be auto-risen
    for button in macro_panel.findChildren(QToolButton):
        assert button.icon() is not None
        assert button.autoRaise()

    # No macros should exist in the table
    assert macro_model.rowCount(mock_index) == 0

    # Recorder has been set to filter out macro panel events
    mock_macro_recorder.add_widget_to_filter_events_out.assert_any_call(macro_panel)
    mock_macro_recorder.add_widget_to_filter_events_out.assert_any_call(
        macro_panel.button_record
    )


def test_macro_panel_toggle_recording(
    macro_panel: MacroPanel,
    macro_model: MacroTableModel,
    mock_input_dialog: "MagicMock",
    mock_macro_recorder: "MagicMock",
    qtbot: "QtBot",
    subtests: "SubTests",
) -> None:
    with subtests.test("Start recording"):
        # Act
        qtbot.mouseClick(macro_panel.button_record, Qt.LeftButton)

        # Assert
        mock_macro_recorder.start_recording.assert_called_once()
        assert macro_panel.button_record.isChecked()

    with subtests.test("Stop recording"):
        # Act
        qtbot.mouseClick(macro_panel.button_record, Qt.LeftButton)

        # Assert
        mock_macro_recorder.stop_recording.assert_called_once()
        assert not macro_panel.button_record.isChecked()
        mock_input_dialog.assert_called_once()


@pytest.mark.usefixtures("record_macro")
def test_macro_panel_recording_should_add_macro_to_table(
    macro_panel: MacroPanel,
    macro_model: MacroTableModel,
    mock_macro: "MagicMock",
    mock_index: "MagicMock",
) -> None:
    assert macro_model.macros == [mock_macro]
    assert macro_model.rowCount(mock_index) == 1
    # Not enabled yet since no macro is selected from table
    assert not macro_panel.table_view.selectedIndexes()
    assert not macro_panel.button_play.isEnabled()
    assert not macro_panel.button_delete.isEnabled()


@pytest.mark.usefixtures("record_macro", "set_macro_selected")
def test_selecting_macro_should_make_macro_buttons_enabled(
    macro_panel: MacroPanel,
    macro_model: MacroTableModel,
) -> None:
    assert macro_panel.table_view.selectedIndexes() == [macro_model.index(0, 0)]
    assert macro_panel.button_play.isEnabled()
    assert macro_panel.button_delete.isEnabled()


@pytest.mark.usefixtures("record_macro", "set_macro_selected")
def test_macro_panel_play_macro(
    macro_panel: MacroPanel,
    mock_macro_player: "MagicMock",
    mock_macro: "MagicMock",
    qtbot: "QtBot",
    mock_profiler: "MagicMock",
    default_group: str,
) -> None:
    # Act
    qtbot.mouseClick(macro_panel.button_play, Qt.LeftButton)

    # Assert
    mock_macro_player.play.assert_called_once_with(mock_macro)
    mock_profiler.profile.assert_called_once_with(f"Macro: {MACRO_NAME}", default_group)
    mock_profiler.profile_recovery_time.assert_called_once_with(
        f"Macro: {MACRO_NAME} (recovery)"
    )


@pytest.mark.usefixtures("record_macro", "set_macro_selected")
def test_macro_panel_delete_macro(
    macro_panel: MacroPanel,
    macro_model: MacroTableModel,
    mock_index: "MagicMock",
    qtbot: "QtBot",
) -> None:
    # Act
    qtbot.mouseClick(macro_panel.button_delete, Qt.LeftButton)

    # Assert
    assert macro_panel.table_view.selectedIndexes() == []
    assert macro_model.macros == []
    assert macro_model.rowCount(mock_index) == 0
