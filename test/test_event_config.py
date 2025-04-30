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
from typing import TYPE_CHECKING, Callable, Optional, Union

import pytest
from pytest_lazy_fixtures import lf
from qgis.PyQt.QtCore import QEvent, QObject, QPoint, Qt
from qgis.PyQt.QtGui import QMouseEvent

from qgis_profiler.config.event_config import (
    AdvancedDigitizingMapToolClickConfig,
    CustomEventFilter,
    EventResponse,
    SimpleMapToolClickConfig,
    SimpleMapToolConfig,
)

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture
    from pytestqt.qtbot import QtBot
    from qgis.gui import QgsMapCanvas


@pytest.fixture
def sample_event() -> QMouseEvent:
    return QMouseEvent(
        QEvent.MouseButtonRelease,
        QPoint(10, 10),
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier,
    )


@pytest.fixture
def sample_object() -> QObject:
    obj = QObject()
    obj.setObjectName("sample_object")
    return obj


@pytest.fixture
def mock_event_filter(mocker: "MockerFixture") -> "MagicMock":
    mock_event_filter = mocker.create_autospec(CustomEventFilter, instance=True)
    mock_event_filter.matches.return_value = True
    mock_event_filter.stop_after_responsive = False
    return mock_event_filter


@pytest.mark.parametrize(
    ("filter_event", "object_filter", "event", "qobject", "expected_result"),
    [
        (
            QEvent.MouseButtonRelease,
            lambda obj: obj.objectName() == "sample_object",
            lf("sample_event"),
            lf("sample_object"),
            True,
        ),
        (
            QMouseEvent(
                QEvent.MouseButtonRelease,
                QPoint(10, 10),
                Qt.LeftButton,
                Qt.LeftButton,
                Qt.NoModifier,
            ),
            lambda obj: obj.objectName() == "sample_object",
            lf("sample_event"),
            lf("sample_object"),
            True,
        ),
        (
            QEvent.MouseButtonRelease,
            None,
            lf("sample_event"),
            lf("sample_object"),
            True,
        ),
        (
            QEvent.KeyPress,
            lambda obj: obj.objectName() == "sample_object",
            lf("sample_event"),
            lf("sample_object"),
            False,
        ),
        (
            QEvent.MouseButtonRelease,
            lambda obj: False,
            lf("sample_event"),
            lf("sample_object"),
            False,
        ),
    ],
)
def test_custom_event_filter(
    filter_event: Union[QEvent, QEvent.Type],
    object_filter: Optional[Callable[[QObject], bool]],
    event: QMouseEvent,
    qobject: QObject,
    expected_result: bool,
):
    # Arrange
    event_filter = CustomEventFilter(filter_event, object_filter)
    # Act
    result = event_filter.matches(event, qobject)
    # Assert
    assert result is expected_result


def test_simple_map_tool_config_should_match_events(
    mock_event_filter: "MagicMock", sample_event: QMouseEvent, sample_object: QObject
):
    config = SimpleMapToolConfig("test", mock_event_filter, mock_event_filter, "name")
    assert not config._profiling_started
    assert config.name == "name"
    assert config.matches(sample_event, sample_object) == EventResponse.START_PROFILING
    assert config._profiling_started
    assert config.matches(sample_event, sample_object) == EventResponse.STOP_PROFILING
    assert config.matches(sample_event, sample_object) == EventResponse.START_PROFILING
    config.activate()
    assert not config._profiling_started


def test_simple_map_tool_config_should_match_events_and_stop_after_responsive(
    mock_event_filter: "MagicMock", sample_event: QMouseEvent, sample_object: QObject
):
    mock_event_filter.stop_after_responsive = True
    config = SimpleMapToolConfig("test", mock_event_filter, mock_event_filter, "name")

    assert config.matches(sample_event, sample_object) == EventResponse.START_PROFILING
    assert (
        config.matches(sample_event, sample_object)
        == EventResponse.STOP_PROFILING_DELAYED
    )


def test_simple_map_tool_config_should_not_match_events(
    mock_event_filter: "MagicMock", sample_event: QMouseEvent, sample_object: QObject
):
    mock_event_filter.matches.return_value = False
    config = SimpleMapToolConfig("test", mock_event_filter, mock_event_filter, "name")
    assert not config.matches(sample_event, sample_object)


@pytest.mark.parametrize(
    ("qobject", "expected_result"),
    [
        (
            lf("qgis_canvas.viewport"),
            EventResponse.START_AND_STOP_DELAYED,
        ),
        (
            QObject,
            None,
        ),
    ],
)
def test_simple_map_tool_click_config_should_match_event(
    mock_event_filter: "MagicMock",
    sample_event: QMouseEvent,
    qobject: Callable[[], QObject],
    expected_result: Optional[EventResponse],
):
    config = SimpleMapToolClickConfig("test")
    assert config.matches(sample_event, qobject()) == expected_result


def test_advanced_digitizing_map_tool_click_config_should_match(
    mock_event_filter: "MagicMock",
    sample_event: QMouseEvent,
    qgis_canvas: "QgsMapCanvas",
):
    config = AdvancedDigitizingMapToolClickConfig("test")
    assert config.initial_canvas_scene_item_count == 0

    assert len(qgis_canvas.scene().items()) == 1
    # The canvas scene count is 1 so match should be found
    assert (
        config.matches(sample_event, qgis_canvas.viewport())
        == EventResponse.START_AND_STOP_DELAYED
    )


def test_advanced_digitizing_map_tool_click_config_should_not_match(
    mock_event_filter: "MagicMock",
    sample_event: QMouseEvent,
    qtbot: "QtBot",
    qgis_canvas: "QgsMapCanvas",
):
    config = AdvancedDigitizingMapToolClickConfig("test")
    assert config.initial_canvas_scene_item_count == 0
    config.activate()
    qtbot.wait(200)

    assert config.initial_canvas_scene_item_count == 1

    assert not config.matches(sample_event, qgis_canvas.viewport())
