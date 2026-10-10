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
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest
from qgis.gui import (
    QgisInterface,
    QgsMapCanvas,
    QgsMapTool,
    QgsMapToolIdentify,
    QgsMapToolPan,
)
from qgis.PyQt.QtCore import QPoint, Qt
from qgis_plugin_tools.utils.typing_utils import require
from qgis_profiler.config.event_config import CustomEventConfig, EventResponse
from qgis_profiler.event_recorder import ProfilerEventRecorder

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from profiler_test_utils.utils import Dialog
    from pytest_mock import MockerFixture
    from pytestqt.qtbot import QtBot
    from qgis_profiler.profiler import ProfilerWrapper


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
    require(qgis_iface.mapCanvas()).setMapTool(map_tool_identify)
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
        qtbot.mouseClick(dialog.button, Qt.MouseButton.LeftButton)
        qtbot.wait(1)

    # Assert
    mock_profiler.start.assert_called_once_with(dialog.button.text(), default_group)
    mock_profiler.end_event.assert_called_once_with(
        mock_profiler.start.return_value, default_group
    )


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
    qtbot.mouseClick(dialog.button, Qt.MouseButton.LeftButton)
    qtbot.wait(1)

    qtbot.mouseMove(dialog.button2)
    qtbot.mouseClick(dialog.button2, Qt.MouseButton.LeftButton)
    qtbot.wait(1)

    # Assert
    mock_profiler.start.assert_any_call(dialog.button.text(), default_group)
    mock_profiler.start.assert_any_call(dialog.button2.text(), default_group)
    assert mock_profiler.end_event.call_count == 2


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
    qtbot.mouseClick(dialog.button, Qt.MouseButton.LeftButton)
    event_recorder.stop_recording()

    # Assert
    mock_profiler.start.assert_any_call(dialog.button.text(), default_group)
    mock_profiler.end_all.assert_called_once_with(default_group)


def test_recorder_should_handle_stop_without_start(
    event_recorder: ProfilerEventRecorder,
) -> None:
    # Should not throw any error.
    event_recorder.stop_recording()


@pytest.mark.parametrize("release_only_or_right_click", ["release_only", "right_click"])
def test_recorder_should_not_start_profiling_if_button_will_not_be_clicked(
    event_recorder: ProfilerEventRecorder,
    mock_profiler: "MagicMock",
    dialog: "Dialog",
    qtbot: "QtBot",
    release_only_or_right_click: str,
) -> None:
    """A release which does not emit clicked must not start a profile.

    Otherwise the profile would never be stopped and it would accumulate
    the time of every event that follows.
    """
    # Arrange
    event_recorder.start_recording()
    qtbot.mouseMove(dialog.button)

    # Act
    if release_only_or_right_click == "release_only":
        # Mouse was pressed somewhere else and released over the button
        qtbot.mouseRelease(dialog.button, Qt.MouseButton.LeftButton)
    else:
        qtbot.mouseClick(dialog.button, Qt.MouseButton.RightButton)
    qtbot.wait(1)

    # Assert
    mock_profiler.start.assert_not_called()
    mock_profiler.end_event.assert_not_called()


@pytest.mark.parametrize("button_name", ["check_box", "radio_button"])
def test_recorder_should_not_start_profiling_if_released_outside_click_area(
    event_recorder: ProfilerEventRecorder,
    mock_profiler: "MagicMock",
    dialog: "Dialog",
    qtbot: "QtBot",
    default_group: str,
    button_name: str,
) -> None:
    """Check boxes and radio buttons only click within the indicator and label.

    The widget stretches wider than that in a layout, so a release over the
    empty area must not start a profile (the button never emits clicked).
    """
    # Arrange
    button = getattr(dialog, button_name)
    assert button.width() > 2 * button.sizeHint().width()
    on_indicator = QPoint(5, button.height() // 2)
    on_empty_area = QPoint(button.width() - 2, button.height() // 2)
    event_recorder.start_recording()

    # Act
    qtbot.mousePress(button, Qt.MouseButton.LeftButton, pos=on_indicator)
    qtbot.mouseRelease(button, Qt.MouseButton.LeftButton, pos=on_empty_area)
    qtbot.wait(1)

    # Assert
    assert not button.isChecked()
    mock_profiler.start.assert_not_called()

    # Act: a real click is still profiled
    with qtbot.waitSignal(event_recorder.event_finished, timeout=100):
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton, pos=on_indicator)

    # Assert
    assert button.isChecked()
    mock_profiler.start.assert_called_once_with(button.text(), default_group)
    mock_profiler.end_event.assert_called_once()


def test_recorder_stop_should_only_end_the_event_it_was_meant_for(
    event_recorder: ProfilerEventRecorder,
    profiler: "ProfilerWrapper",
    qtbot: "QtBot",
    default_group: str,
) -> None:
    """A stop for an event that was never started must not end another event."""
    # Arrange
    event_recorder.start_recording()
    event_recorder._start_profiling("Started event")
    qtbot.wait(10)

    # Act
    with qtbot.assertNotEmitted(event_recorder.event_finished):
        event_recorder._stop_profiling("Never started event", default_group)

    # Assert
    assert profiler.is_profiling(default_group)
    with qtbot.waitSignal(event_recorder.event_finished):
        event_recorder._stop_profiling("Started event", default_group)
    assert not profiler.is_profiling(default_group)


def test_recorder_should_not_accumulate_time_of_other_events(
    event_recorder: ProfilerEventRecorder,
    profiler: "ProfilerWrapper",
    dialog: "Dialog",
    qtbot: "QtBot",
    default_group: str,
) -> None:
    """Regression test for profiles accumulating time from other events.

    Previously a mouse release over a button started a profile even when the
    button did not emit clicked. The profile stayed open, later events were
    nested under it and it was finally ended with their accumulated time.
    """
    # Arrange
    event_recorder.start_recording()

    # Act
    # Release over the first button without pressing it (no clicked)
    qtbot.mouseMove(dialog.button)
    qtbot.mouseRelease(dialog.button, Qt.MouseButton.LeftButton)
    qtbot.wait(1)
    # Properly click the second button
    qtbot.mouseMove(dialog.button2)
    with qtbot.waitSignal(event_recorder.event_finished, timeout=100):
        qtbot.mouseClick(dialog.button2, Qt.MouseButton.LeftButton)
        qtbot.wait(1)
    event_recorder.stop_recording()

    # Assert
    results = profiler.get_profiler_data(group=default_group)
    assert [result.name for result in results] == [dialog.button2.text()]
    assert results[0].children == []
    assert results[0].duration < 0.1


def test_recorder_should_handle_map_tool_change(
    event_recorder: ProfilerEventRecorder,
    map_tool_pan: "QgsMapTool",
    map_tool_identify: "QgsMapTool",
    qgis_canvas: "QgsMapCanvas",
) -> None:
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
    response: EventResponse | None,
    expected_methods_to_call: list[str],
) -> None:
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
