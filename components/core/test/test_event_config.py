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
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest
from pytest_lazy_fixtures import lf
from qgis.core import (
    QgsEditFormConfig,
    QgsPointXY,
    QgsProject,
    QgsSettings,
    QgsVectorLayer,
)
from qgis.gui import (
    QgsAdvancedDigitizingDockWidget,
    QgsMapToolCapture,
    QgsMapToolDigitizeFeature,
)
from qgis.PyQt.QtCore import QEvent, QObject, QPointF, Qt
from qgis.PyQt.QtGui import QMouseEvent
from qgis_plugin_tools.utils.typing_utils import require
from qgis_profiler.config.event_config import (
    DEFAULT_MAP_TOOLS_CONFIG,
    AdvancedDigitizingMapToolClickConfig,
    CustomEventFilter,
    EventResponse,
    SimpleMapToolClickConfig,
    SimpleMapToolConfig,
    digitizing_will_show_feature_form,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture
    from pytestqt.qtbot import QtBot
    from qgis.gui import QgsMapCanvas


@pytest.fixture
def line_layer() -> "Iterator[QgsVectorLayer]":
    layer = QgsVectorLayer(
        "LineString?crs=EPSG:4326&field=name:string", "lines", "memory"
    )
    assert layer.isValid()
    assert QgsProject.instance().addMapLayer(layer) is layer
    yield layer
    QgsProject.instance().removeMapLayer(layer.id())


@pytest.fixture
def digitize_line_tool(
    qgis_canvas: "QgsMapCanvas", line_layer: QgsVectorLayer, qtbot: "QtBot"
) -> "Iterator[QgsMapToolDigitizeFeature]":
    qgis_canvas.setLayers([line_layer])
    qgis_canvas.setCurrentLayer(line_layer)
    # The canvas owns the dock widget and the tool
    cad_dock_widget = QgsAdvancedDigitizingDockWidget(qgis_canvas, qgis_canvas)
    tool = QgsMapToolDigitizeFeature(
        qgis_canvas, cad_dock_widget, QgsMapToolCapture.CaptureMode.CaptureLine
    )
    tool.setLayer(line_layer)
    qgis_canvas.setMapTool(tool)
    yield tool
    qgis_canvas.unsetMapTool(tool)
    # Delete the tool before the canvas scene deletes its rubber bands
    tool.deleteLater()
    qtbot.wait(1)


@pytest.fixture
def sample_event() -> QMouseEvent:
    return QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(10, 10),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
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
            QEvent.Type.MouseButtonRelease,
            lambda obj: obj.objectName() == "sample_object",
            lf("sample_event"),
            lf("sample_object"),
            True,
        ),
        (
            QMouseEvent(
                QEvent.Type.MouseButtonRelease,
                QPointF(10, 10),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            ),
            lambda obj: obj.objectName() == "sample_object",
            lf("sample_event"),
            lf("sample_object"),
            True,
        ),
        (
            QEvent.Type.MouseButtonRelease,
            None,
            lf("sample_event"),
            lf("sample_object"),
            True,
        ),
        (
            QEvent.Type.KeyPress,
            lambda obj: obj.objectName() == "sample_object",
            lf("sample_event"),
            lf("sample_object"),
            False,
        ),
        (
            QEvent.Type.MouseButtonRelease,
            lambda obj: False,
            lf("sample_event"),
            lf("sample_object"),
            False,
        ),
    ],
)
def test_custom_event_filter(
    filter_event: QEvent | QEvent.Type,
    object_filter: Callable[[QObject], bool] | None,
    event: QMouseEvent,
    qobject: QObject,
    expected_result: bool,
) -> None:
    # Arrange
    event_filter = CustomEventFilter(filter_event, object_filter)
    # Act
    result = event_filter.matches(event, qobject)
    # Assert
    assert result is expected_result


def test_simple_map_tool_config_should_match_events(
    mock_event_filter: "MagicMock", sample_event: QMouseEvent, sample_object: QObject
) -> None:
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
) -> None:
    mock_event_filter.stop_after_responsive = True
    config = SimpleMapToolConfig("test", mock_event_filter, mock_event_filter, "name")

    assert config.matches(sample_event, sample_object) == EventResponse.START_PROFILING
    assert (
        config.matches(sample_event, sample_object)
        == EventResponse.STOP_PROFILING_DELAYED
    )


def test_simple_map_tool_config_should_not_match_events(
    mock_event_filter: "MagicMock", sample_event: QMouseEvent, sample_object: QObject
) -> None:
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
    expected_result: EventResponse | None,
) -> None:
    config = SimpleMapToolClickConfig("test")
    assert config.matches(sample_event, qobject()) == expected_result


def test_advanced_digitizing_map_tool_click_config_should_match(
    mock_event_filter: "MagicMock",
    sample_event: QMouseEvent,
    qgis_canvas: "QgsMapCanvas",
) -> None:
    config = AdvancedDigitizingMapToolClickConfig("test")
    assert config.initial_canvas_scene_item_count == 0

    assert len(require(qgis_canvas.scene()).items()) == 1
    # The canvas scene count is 1 so match should be found
    assert (
        config.matches(sample_event, require(qgis_canvas.viewport()))
        == EventResponse.START_AND_STOP_DELAYED
    )


def test_advanced_digitizing_map_tool_click_config_should_not_match(
    mock_event_filter: "MagicMock",
    sample_event: QMouseEvent,
    qtbot: "QtBot",
    qgis_canvas: "QgsMapCanvas",
) -> None:
    config = AdvancedDigitizingMapToolClickConfig("test")
    assert config.initial_canvas_scene_item_count == 0
    config.activate()
    qtbot.wait(200)

    assert config.initial_canvas_scene_item_count == 1

    assert not config.matches(sample_event, qgis_canvas.viewport())


def test_default_digitize_config_should_start_only_if_feature_form_will_be_shown(
    sample_event: QMouseEvent, qgis_canvas: "QgsMapCanvas"
) -> None:
    config = DEFAULT_MAP_TOOLS_CONFIG["QgsMapToolDigitizeFeature"]
    assert isinstance(config, SimpleMapToolConfig)
    assert config.start_event_filter.object_filter is digitizing_will_show_feature_form


def test_digitizing_should_not_show_feature_form_without_digitize_tool(
    qgis_canvas: "QgsMapCanvas",
) -> None:
    assert not digitizing_will_show_feature_form(qgis_canvas.viewport())


def test_digitizing_should_show_feature_form_only_with_enough_vertices(
    qgis_canvas: "QgsMapCanvas", digitize_line_tool: QgsMapToolDigitizeFeature
) -> None:
    viewport = qgis_canvas.viewport()

    # Right click before any vertex: nothing is digitized and no form is shown
    assert not digitizing_will_show_feature_form(viewport)
    assert not digitizing_will_show_feature_form(QObject())

    assert digitize_line_tool.addVertex(QgsPointXY(0, 0)) == 0
    assert not digitizing_will_show_feature_form(viewport)

    assert digitize_line_tool.addVertex(QgsPointXY(1, 1)) == 0
    assert digitizing_will_show_feature_form(viewport)


@pytest.mark.parametrize(
    ("suppress", "disable_dialog_setting", "expected_result"),
    [
        (QgsEditFormConfig.FeatureFormSuppress.SuppressDefault, False, True),
        (QgsEditFormConfig.FeatureFormSuppress.SuppressDefault, True, False),
        (QgsEditFormConfig.FeatureFormSuppress.SuppressOn, False, False),
        (QgsEditFormConfig.FeatureFormSuppress.SuppressOff, True, True),
    ],
)
def test_digitizing_should_not_show_feature_form_if_suppressed(
    qgis_canvas: "QgsMapCanvas",
    line_layer: QgsVectorLayer,
    digitize_line_tool: QgsMapToolDigitizeFeature,
    suppress: QgsEditFormConfig.FeatureFormSuppress,
    disable_dialog_setting: bool,
    expected_result: bool,
) -> None:
    # Arrange
    form_config = line_layer.editFormConfig()
    form_config.setSuppress(suppress)
    line_layer.setEditFormConfig(form_config)
    settings = QgsSettings()
    setting_key = "qgis/digitizing/disable_enter_attribute_values_dialog"
    settings.setValue(setting_key, disable_dialog_setting)
    assert digitize_line_tool.addVertex(QgsPointXY(0, 0)) == 0
    assert digitize_line_tool.addVertex(QgsPointXY(1, 1)) == 0

    # Act
    try:
        result = digitizing_will_show_feature_form(qgis_canvas.viewport())
    finally:
        settings.remove(setting_key)

    # Assert
    assert result is expected_result
