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

from qgis_profiler.event_recorder import ProfilerEventRecorder

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytestqt.qtbot import QtBot

    from profiler_test_utils.utils import Dialog


@pytest.fixture
def event_recorder(default_group: str) -> Iterator[ProfilerEventRecorder]:
    recorder = ProfilerEventRecorder(group_name=default_group)
    yield recorder
    recorder.stop_recording()


def test_recorder_should_profile_button_click(
    event_recorder: ProfilerEventRecorder,
    mock_profiler: "MagicMock",
    dialog: "Dialog",
    qtbot: "QtBot",
    default_group: str,
) -> None:
    # Arrange
    event_recorder.start_recording()

    # Act
    qtbot.mouseMove(dialog.button)
    with qtbot.waitSignal(event_recorder.event_finished, timeout=100):
        qtbot.mouseClick(dialog.button, Qt.LeftButton)
        qtbot.wait(1)

    # Assert
    mock_profiler.start.assert_called_once_with(dialog.button.text(), default_group)
    mock_profiler.end.assert_called_once_with(default_group)


def test_recorder_should_handle_multiple_button_clicks(
    event_recorder: ProfilerEventRecorder,
    mock_profiler: "MagicMock",
    dialog: "Dialog",
    qtbot: "QtBot",
    default_group: str,
) -> None:
    # Arrange
    event_recorder.start_recording()

    # Act
    qtbot.mouseMove(dialog.button)
    qtbot.mouseClick(dialog.button, Qt.LeftButton)
    qtbot.wait(1)

    qtbot.mouseMove(dialog.button2)
    qtbot.mouseClick(dialog.button2, Qt.LeftButton)
    qtbot.wait(1)

    # Assert
    mock_profiler.start.assert_any_call(dialog.button.text(), default_group)
    mock_profiler.start.assert_any_call(dialog.button2.text(), default_group)
    assert mock_profiler.end.call_count == 2


def test_recorder_should_stop_gracefully_if_recording_is_in_progress(
    event_recorder: ProfilerEventRecorder,
    mock_profiler: "MagicMock",
    dialog: "Dialog",
    qtbot: "QtBot",
    default_group: str,
) -> None:
    # Arrange
    event_recorder.start_recording()

    # Act
    qtbot.mouseMove(dialog.button)
    qtbot.mouseClick(dialog.button, Qt.LeftButton)
    event_recorder.stop_recording()

    # Assert
    mock_profiler.start.assert_any_call(dialog.button.text(), default_group)
    mock_profiler.end.assert_called_once_with(default_group)


def test_recorder_should_handle_stop_without_start(
    event_recorder: ProfilerEventRecorder,
) -> None:
    # Should not throw any error.
    event_recorder.stop_recording()
