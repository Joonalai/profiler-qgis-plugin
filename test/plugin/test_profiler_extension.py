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

import pytest
from pytest_mock import MockerFixture
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from profiler_plugin.ui.profiler_extension import ProfilerExtension
from profiler_plugin.ui.settings_dialog import SettingsDialog
from qgis_profiler.event_recorder import ProfilerEventRecorder

TEST_GROUP = "TestGroup"

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_subtests import SubTests
    from pytestqt.qtbot import QtBot


class StubProfilerPanel(QDialog):
    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowTitle("Stub profiler panel")
        self.setFixedSize(200, 150)
        self.vbox_layout = QVBoxLayout(self)
        self.combo_box_group = QComboBox(self)
        self.combo_box_group.addItems(["Group 1", "Group 2"])
        self.vbox_layout.addWidget(self.combo_box_group)


@pytest.fixture
def mock_event_recorder(mocker: MockerFixture) -> "MagicMock":
    mock_event_recorder = mocker.create_autospec(ProfilerEventRecorder, instance=True)
    # Recording is in progress if start_recording
    # has been called more than stop_recording
    mock_event_recorder.is_recording = (
        lambda: mock_event_recorder.start_recording.call_count
        > mock_event_recorder.stop_recording.call_count
    )
    mock_event_recorder.group = TEST_GROUP
    return mock_event_recorder


@pytest.fixture
def mock_settings_dialog(mocker: MockerFixture) -> "MagicMock":
    mock_settings_dialog = mocker.create_autospec(SettingsDialog, instance=True)
    mocker.patch(
        "profiler_plugin.ui.profiler_extension.SettingsDialog",
        return_value=mock_settings_dialog,
    )
    return mock_settings_dialog


@pytest.fixture
def stub_profiler_panel(qtbot: "QtBot") -> StubProfilerPanel:
    stub_widget = StubProfilerPanel()
    qtbot.addWidget(stub_widget)
    stub_widget.show()
    return stub_widget


@pytest.fixture
def _modify_mock_profiler(
    mock_profiler: "MagicMock", stub_profiler_panel: StubProfilerPanel
) -> None:
    mock_profiler.create_group.side_effect = (
        lambda group: stub_profiler_panel.combo_box_group.addItem(group)
    )


@pytest.fixture
def profiler_extension(
    mock_event_recorder: "MagicMock",
    mock_settings_dialog: "MagicMock",
    _modify_mock_profiler: None,
    stub_profiler_panel: StubProfilerPanel,
) -> ProfilerExtension:
    profiler_extension = ProfilerExtension(
        event_recorder=mock_event_recorder,
        profiler_panel=cast("QWidget", stub_profiler_panel),
    )
    stub_profiler_panel.vbox_layout.insertWidget(0, profiler_extension)
    return profiler_extension


def test_profiler_extension_initialization(
    stub_profiler_panel: QWidget,
    profiler_extension: ProfilerExtension,
) -> None:
    # Assert
    assert stub_profiler_panel.findChild(ProfilerExtension) == profiler_extension
    assert profiler_extension.combo_box_group.count() == 2
    assert profiler_extension.combo_box_group.itemText(0) == "Group 1"
    assert profiler_extension.button_record.isEnabled()
    assert not profiler_extension.button_record.isChecked()
    # Not enabled for existing groups
    assert not profiler_extension.button_clear.isEnabled()
    assert not profiler_extension.button_save.isEnabled()
    assert profiler_extension.button_settings.isEnabled()

    # All buttons should have icons and be auto-risen
    for button in profiler_extension.findChildren(QToolButton):
        assert button.icon() is not None
        assert button.autoRaise()


def test_toggle_recording(
    profiler_extension: ProfilerExtension,
    mock_event_recorder: "MagicMock",
    mock_profiler: "MagicMock",
    stub_profiler_panel: StubProfilerPanel,
    qtbot: "QtBot",
    subtests: "SubTests",
) -> None:
    with subtests.test("Start recording"):
        # Act
        qtbot.mouseClick(profiler_extension.button_record, Qt.LeftButton)

        # Assert
        mock_event_recorder.start_recording.assert_called_once()
        mock_profiler.create_group.assert_called_once_with(TEST_GROUP)
        assert profiler_extension.button_record.isChecked()
        assert stub_profiler_panel.combo_box_group.currentText() == TEST_GROUP

    with subtests.test("Stop recording"):
        # Act
        qtbot.mouseClick(profiler_extension.button_record, Qt.LeftButton)

        # Assert
        mock_event_recorder.stop_recording.assert_called_once()
        assert not profiler_extension.button_record.isChecked()

    assert profiler_extension.button_clear.isEnabled()


def test_clear_button_should_clear_current_group(
    profiler_extension: ProfilerExtension,
    mock_profiler: "MagicMock",
    qtbot: "QtBot",
) -> None:
    # Arrange
    qtbot.mouseClick(profiler_extension.button_record, Qt.LeftButton)
    assert profiler_extension.button_clear.isEnabled()

    # Act
    qtbot.mouseClick(profiler_extension.button_clear, Qt.LeftButton)

    # Assert
    mock_profiler.clear.assert_called_once_with(TEST_GROUP)


def test_button_settings_should_open_settings_dialog(
    profiler_extension: ProfilerExtension,
    mock_settings_dialog: "MagicMock",
    qtbot: "QtBot",
) -> None:
    # Act
    qtbot.mouseClick(profiler_extension.button_settings, Qt.LeftButton)

    # Assert
    mock_settings_dialog.show.assert_called_once()
