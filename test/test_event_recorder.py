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
from typing import TYPE_CHECKING, Optional

import pytest
from qgis.gui import (
    QgisInterface,
    QgsMapCanvas,
    QgsMapTool,
    QgsMapToolIdentify,
    QgsMapToolPan,
)
from qgis.PyQt.QtCore import Qt

from qgis_profiler.config.event_config import CustomEventConfig, EventResponse
from qgis_profiler.event_recorder import ProfilerEventRecorder

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture
    from pytestqt.qtbot import QtBot

    from profiler_test_utils.utils import Dialog


@pytest.fixture
def map_tool_identify(qgis_canvas: "QgsMapCanvas") -> "QgsMapTool":
    return QgsMapToolIdentify(qgis_canvas)


@pytest.fixture
def map_tool_pan(qgis_canvas: "QgsMapCanvas") -> "QgsMapTool":
    return QgsMapToolPan(qgis_canvas)


@pytest.fixture
def mock_event_config(mocker: "MockerFixture") -> "MagicMock":
    mock_event_config = mocker.create_autospec(CustomEventConfig, instance=True)
    mock_event_config.name = "mock config"
    return mock_event_config


@pytest.fixture
def event_recorder(
    default_group: str, map_tool_identify: "QgsMapTool", qgis_iface: "QgisInterface"
) -> Iterator[ProfilerEventRecorder]:
    qgis_iface.mapCanvas().setMapTool(map_tool_identify)
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
    mock_profiler.end_all.assert_called_once_with(default_group)
    mock_profiler.reset_mock()

    # Act
    qtbot.mouseMove(dialog.button)
    qtbot.mouseClick(dialog.button, Qt.LeftButton)
    event_recorder.stop_recording()

    # Assert
    mock_profiler.start.assert_any_call(dialog.button.text(), default_group)
    mock_profiler.end_all.assert_called_once_with(default_group)


def test_recorder_should_handle_stop_without_start(
    event_recorder: ProfilerEventRecorder,
) -> None:
    # Should not throw any error.
    event_recorder.stop_recording()


def test_recorder_should_handle_map_tool_change(
    event_recorder: ProfilerEventRecorder,
    map_tool_pan: "QgsMapTool",
    map_tool_identify: "QgsMapTool",
    qgis_canvas: "QgsMapCanvas",
):
    # Arrange
    event_recorder.start_recording()
    assert event_recorder._current_map_tool_config
    assert event_recorder._current_map_tool_config.name == "QgsMapToolIdentify"

    # Act
    qgis_canvas.setMapTool(map_tool_pan)

    # Assert
    assert event_recorder._current_map_tool_config.name == "QgsMapToolPan"


@pytest.mark.parametrize(
    "attribute_to_mock", ["_current_map_tool_config", "_general_map_tools_config"]
)
@pytest.mark.parametrize(
    ("response", "expected_methods_to_call"),
    [
        (None, []),
        (EventResponse.START_PROFILING, ["_start_profiling"]),
        (EventResponse.STOP_PROFILING, ["_stop_profiling"]),
        (EventResponse.STOP_PROFILING_DELAYED, ["_post_stop_profiling_event"]),
        (
            EventResponse.START_AND_STOP_DELAYED,
            ["_start_profiling", "_post_stop_profiling_event"],
        ),
    ],
)
def test_recorder_should_record_map_tool_events(
    event_recorder: ProfilerEventRecorder,
    mock_event_config: "MagicMock",
    dialog: "Dialog",
    qtbot: "QtBot",
    mocker: "MockerFixture",
    attribute_to_mock: str,
    response: Optional[EventResponse],
    expected_methods_to_call: list[str],
):
    # Arrange
    mock_event_config.matches.return_value = response
    event_recorder.start_recording()
    if attribute_to_mock == "_general_map_tools_config":
        mock_event_config = [mock_event_config]  # type: ignore
    setattr(event_recorder, attribute_to_mock, mock_event_config)
    spies = [mocker.spy(event_recorder, method) for method in expected_methods_to_call]

    # Act
    qtbot.wait(1)

    # Assert
    for spy in spies:
        spy.assert_called()
