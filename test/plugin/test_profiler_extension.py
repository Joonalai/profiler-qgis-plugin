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
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest
from pytest_mock import MockerFixture
from qgis.PyQt.QtCore import QStringListModel, Qt
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from profiler_plugin.ui.profiler_extension import ProfilerExtension
from profiler_plugin.ui.settings_dialog import SettingsDialog
from qgis_profiler.settings import ProfilerSettings

NEW_GROUP = "New manual group"
INITIAL_GROUPS = ["Manual group", "QGIS group"]

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
        self.combo_box_group.addItems(INITIAL_GROUPS)
        self.combo_box_group.setCurrentIndex(0)
        self.vbox_layout.addWidget(self.combo_box_group)
        self.tree_view = QTreeView(self)
        self.vbox_layout.addWidget(self.tree_view)


@pytest.fixture
def mock_event_recorder(mocker: MockerFixture) -> "MagicMock":
    mock_event_recorder = mocker.MagicMock()
    # Recording is in progress if start_recording
    # has been called more than stop_recording
    mock_event_recorder.is_recording = (
        lambda: mock_event_recorder.start_recording.call_count
        > mock_event_recorder.stop_recording.call_count
    )
    mock_event_recorder.group = NEW_GROUP
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
def item_model() -> QStringListModel:
    model = QStringListModel()
    model.setStringList([*INITIAL_GROUPS])
    return model


@pytest.fixture
def _modify_mock_profiler(
    mock_profiler: "MagicMock",
    stub_profiler_panel: StubProfilerPanel,
    item_model: QStringListModel,
) -> None:
    mock_profiler.create_group.side_effect = (
        lambda group: stub_profiler_panel.combo_box_group.addItem(group)
    )
    mock_profiler.item_model.return_value = item_model
    mock_profiler.qgis_groups.return_value = {
        "QGIS group": "qgis-group",
    }


@pytest.fixture
def profiler_extension(
    mock_event_recorder: "MagicMock",
    mock_settings_dialog: "MagicMock",
    mock_meter_recovery_measurer: "MagicMock",
    mock_thread_health_checker_meter: "MagicMock",
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
    stub_profiler_panel: QWidget, profiler_extension: ProfilerExtension
) -> None:
    # Assert
    assert stub_profiler_panel.findChild(ProfilerExtension) == profiler_extension
    assert profiler_extension.combo_box_group.count() == 2
    assert profiler_extension.combo_box_group.itemText(0) == INITIAL_GROUPS[0]
    assert profiler_extension._current_group() == INITIAL_GROUPS[0]
    assert profiler_extension.button_record.isEnabled()
    assert profiler_extension.button_cprofiler_record.isEnabled()
    assert profiler_extension.button_save.isEnabled()
    assert not profiler_extension.button_record.isChecked()
    assert len(profiler_extension._meters) == 2
    assert profiler_extension.button_clear.isEnabled()
    assert profiler_extension.button_settings.isEnabled()
    assert not profiler_extension.filter_line_edit.value()
    assert profiler_extension._filter_proxy_model.group == INITIAL_GROUPS[0]

    # All buttons should have icons and be auto-risen
    for button in profiler_extension.findChildren(QToolButton):
        assert button.icon() is not None


def test_toggle_recording(
    profiler_extension: ProfilerExtension,
    mock_event_recorder: "MagicMock",
    mock_profiler: "MagicMock",
    mock_thread_health_checker_meter: "MagicMock",
    stub_profiler_panel: StubProfilerPanel,
    qtbot: "QtBot",
    subtests: "SubTests",
) -> None:
    with subtests.test("Start recording"):
        # Act
        qtbot.mouseClick(profiler_extension.button_record, Qt.LeftButton)

        # Assert
        mock_event_recorder.start_recording.assert_called_once()
        mock_profiler.create_group.assert_called_once_with(NEW_GROUP)
        mock_thread_health_checker_meter.start_measuring.assert_called_once()
        assert profiler_extension.button_record.isChecked()
        assert stub_profiler_panel.combo_box_group.currentText() == NEW_GROUP
        assert profiler_extension._filter_proxy_model.group == NEW_GROUP

    with subtests.test("Stop recording"):
        # Act
        qtbot.mouseClick(profiler_extension.button_record, Qt.LeftButton)

        # Assert
        mock_event_recorder.stop_recording.assert_called_once()
        mock_thread_health_checker_meter.stop_measuring.assert_called_once()
        assert not profiler_extension.button_record.isChecked()

    assert profiler_extension.button_clear.isEnabled()


def test_toggle_cprofile_recording(
    profiler_extension: ProfilerExtension,
    mock_event_recorder: "MagicMock",
    mock_profiler: "MagicMock",
    mock_thread_health_checker_meter: "MagicMock",
    stub_profiler_panel: StubProfilerPanel,
    qtbot: "QtBot",
    subtests: "SubTests",
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "profile" / "file.prof"
    ProfilerSettings.cprofiler_profile_path.value.default = str(file_path)
    assert not file_path.exists()
    assert not file_path.parent.exists()

    with subtests.test("Start recording"):
        # Act
        qtbot.mouseClick(profiler_extension.button_cprofiler_record, Qt.LeftButton)

        # Assert
        mock_profiler.cprofiler.enable.assert_called_once()
        assert profiler_extension.button_cprofiler_record.isChecked()

    with subtests.test("Stop recording"):
        # Act
        qtbot.wait(19)
        qtbot.mouseClick(profiler_extension.button_cprofiler_record, Qt.LeftButton)

        # Assert
        mock_profiler.cprofiler.disable.assert_called_once()
        mock_profiler.cprofiler.get_stat_report.assert_called_once()
        assert file_path.parent.exists()
        mock_profiler.cprofiler.dump_stats.assert_called_once_with(file_path)
        assert not profiler_extension.button_cprofiler_record.isChecked()


def test_save_results(
    profiler_extension: ProfilerExtension,
    mock_event_recorder: "MagicMock",
    mock_profiler: "MagicMock",
    mock_thread_health_checker_meter: "MagicMock",
    stub_profiler_panel: StubProfilerPanel,
    qtbot: "QtBot",
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    # Arrange
    file_path = tmp_path / "file.prof"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", classmethod(lambda *args: (str(file_path), ""))
    )

    # Act
    qtbot.mouseClick(profiler_extension.button_save, Qt.LeftButton)

    # Assert
    mock_profiler.save_profiler_results_as_prof_file.assert_called_once_with(
        INITIAL_GROUPS[0], file_path
    )


def test_save_results_without_suffix(
    profiler_extension: ProfilerExtension,
    mock_event_recorder: "MagicMock",
    mock_profiler: "MagicMock",
    mock_thread_health_checker_meter: "MagicMock",
    stub_profiler_panel: StubProfilerPanel,
    qtbot: "QtBot",
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    # Arrange
    file_path = tmp_path / "file"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", classmethod(lambda *args: (str(file_path), ""))
    )

    # Act
    qtbot.mouseClick(profiler_extension.button_save, Qt.LeftButton)

    # Assert
    mock_profiler.save_profiler_results_as_prof_file.assert_called_once_with(
        INITIAL_GROUPS[0], file_path.with_suffix(".prof")
    )


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
    mock_profiler.clear.assert_called_once_with(NEW_GROUP)


def test_button_settings_should_open_settings_dialog(
    profiler_extension: ProfilerExtension,
    mock_settings_dialog: "MagicMock",
    mock_meter_recovery_measurer: "MagicMock",
    mock_thread_health_checker_meter: "MagicMock",
    qtbot: "QtBot",
) -> None:
    # Arrange
    mock_meter_recovery_measurer.reset_mock()

    # Act
    qtbot.mouseClick(profiler_extension.button_settings, Qt.LeftButton)

    # Assert
    mock_settings_dialog.exec.assert_called_once()
    mock_meter_recovery_measurer.cleanup.assert_called_once()
    mock_meter_recovery_measurer.reset_parameters.assert_called_once()
    mock_thread_health_checker_meter.cleanup.assert_called_once()
    mock_thread_health_checker_meter.reset_parameters.assert_called()


def test_cleanup_should_clean_meters(
    profiler_extension: ProfilerExtension,
    mock_settings_dialog: "MagicMock",
    mock_meter_recovery_measurer: "MagicMock",
    mock_thread_health_checker_meter: "MagicMock",
) -> None:
    # Act
    profiler_extension.cleanup()

    # Assert
    mock_meter_recovery_measurer.cleanup.assert_called_once()
    mock_thread_health_checker_meter.cleanup.assert_called_once()
    assert profiler_extension._meters == []


def test_changing_group_affects_proxy_model(
    profiler_extension: ProfilerExtension,
) -> None:
    # Act
    profiler_extension.combo_box_group.setCurrentIndex(1)

    # Assert
    profiler_extension._filter_proxy_model.group = "QGIS group"


def test_filter_line_edit_should_filter(
    profiler_extension: ProfilerExtension, qtbot: "QtBot"
) -> None:
    # Act
    qtbot.keyClicks(profiler_extension.filter_line_edit, "Manual")

    # Assert
    profiler_extension._filter_proxy_model.group = "QGIS group"
    assert profiler_extension._filter_proxy_model.filterRegExp().pattern() == "Manual"
