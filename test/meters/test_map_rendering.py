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
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QTimer

from qgis_profiler.meters.map_rendering import MapRenderingMeter

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytestqt.qtbot import QtBot


@pytest.fixture
def meter(
    mock_profiler: "MagicMock",
) -> Iterator[MapRenderingMeter]:
    meter = MapRenderingMeter(0.05)
    yield meter
    meter.cleanup()  # Ensure the measuring is stopped
    assert meter.is_measuring is False


def test_map_rendering_meter_should_measure_map_rendering_time(
    meter: MapRenderingMeter, qgis_canvas: QgsMapCanvas, qtbot: "QtBot"
):
    with (
        qtbot.waitSignal(qgis_canvas.renderStarting, timeout=100),
        qtbot.waitSignal(qgis_canvas.mapCanvasRefreshed, timeout=100),
    ):
        QTimer.singleShot(1, qgis_canvas.renderStarting.emit)
        QTimer.singleShot(10, qgis_canvas.mapCanvasRefreshed.emit)

        assert meter.measure() == pytest.approx(0.1, abs=1e-1)


def test_map_rendering_meter_should_start_measuring(
    meter: MapRenderingMeter, qgis_canvas: "QgsMapCanvas", qtbot: "QtBot"
):
    meter.start_measuring()
    with (
        qtbot.waitSignal(qgis_canvas.renderStarting),
        qtbot.waitSignal(qgis_canvas.mapCanvasRefreshed),
        qtbot.waitSignal(meter.anomaly_detected, timeout=1000),
    ):
        QTimer.singleShot(1, qgis_canvas.renderStarting.emit)
        QTimer.singleShot(60, qgis_canvas.mapCanvasRefreshed.emit)
