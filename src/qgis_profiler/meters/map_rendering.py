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
import logging
import time
from contextlib import suppress
from typing import TYPE_CHECKING, Optional, cast

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QElapsedTimer
from qgis.utils import iface as iface_

from qgis_profiler.meters.meter import Meter
from qgis_profiler.settings import ProfilerSettings

if TYPE_CHECKING:
    from qgis.gui import QgisInterface

LOGGER = logging.getLogger(__name__)

iface = cast("QgisInterface", iface_)


class MapRenderingMeter(Meter):
    """
    Measures the time it takes to fully render the map.
    """

    _short_name = "rendering"
    _instance: Optional["MapRenderingMeter"] = None

    def __init__(
        self,
        threshold_s: float,
    ) -> None:
        super().__init__(supports_continuous_measurement=True)
        self._threshold_ms = threshold_s * 1000
        self._elapsed_timer = QElapsedTimer()
        self._last_rendering_time_ms: int = 0
        LOGGER.debug("MapRenderingMeasurer parameters initialized: %s", self)

    def __str__(self) -> str:
        return f"MapRenderingMeasurer(threshold_s={self._threshold_ms / 1000}),"

    @classmethod
    def get(cls) -> "MapRenderingMeter":
        if cls._instance is None:
            cls._instance = MapRenderingMeter(
                threshold_s=ProfilerSettings.map_rendering_meter_threshold.get(),
            )
            cls._instance.enabled = ProfilerSettings.map_rendering_meter_enabled.get()
        return cls._instance

    def reset_parameters(self) -> None:
        self._threshold_ms = ProfilerSettings.map_rendering_meter_threshold.get() * 1000
        self.enabled = ProfilerSettings.map_rendering_meter_enabled.get()
        LOGGER.debug("MapRenderingMeasurer parameters reset: %s", self)

    def _start_measuring(self) -> bool:
        LOGGER.debug("Starting map rendering measuring")
        iface.mapCanvas().renderStarting.connect(self._rendering_started)
        iface.mapCanvas().mapCanvasRefreshed.connect(self._rendering_finished)
        return True

    def _stop_measuring(self) -> None:
        with suppress(TypeError):
            iface.mapCanvas().renderStarting.disconnect(self._rendering_started)
        with suppress(TypeError):
            iface.mapCanvas().renderStarting.disconnect(self._rendering_started)

    def _rendering_started(self) -> None:
        self._elapsed_timer.restart()

    def _rendering_finished(self) -> None:
        elapsed_ms = self._elapsed_timer.elapsed()
        if elapsed_ms > self._threshold_ms:
            LOGGER.debug("Map rendering time exceeded threshold %s ms", elapsed_ms)
            self._emit_anomaly(round(elapsed_ms / 1000, 3))
        self._last_rendering_time_ms = elapsed_ms

    def _measure(self) -> tuple[float, bool]:
        if self.is_measuring:
            return (
                self._last_rendering_time_ms / 1000,
                self._last_rendering_time_ms > self._threshold_ms,
            )
        self._last_rendering_time_ms = 0
        self.start_measuring()
        iface.mapCanvas().redrawAllLayers()
        t = time.time()
        timeout = 10

        while self._last_rendering_time_ms == 0 and time.time() - t < timeout:
            QgsApplication.processEvents()
        rendering_time = (self._last_rendering_time_ms / 1000) or timeout
        return rendering_time, rendering_time > self._threshold_ms * 1000
