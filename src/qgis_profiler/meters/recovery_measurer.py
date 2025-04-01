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

from qgis.PyQt.QtCore import QCoreApplication, QElapsedTimer

from qgis_profiler.meters.meter import Meter

LOGGER = logging.getLogger(__name__)


class RecoveryMeasurer(Meter):
    """
    Sometimes QGIS freezes and becomes slow for a short period of
    time. This meter measures how much time it takes for QGIS to
    become fully responsive again.
    """

    def __init__(
        self,
        process_event_count: int,
        normal_time_s: int,
        timeout_s: int,
        context: str,
    ) -> None:
        super().__init__()
        self._process_event_count = process_event_count
        self._normal_time_ms = normal_time_s * 1000
        self._timeout_ms = timeout_s * 1000
        self._context = context
        self._elapsed_timer = QElapsedTimer()
        self._recovery_timer = QElapsedTimer()

    def measure(self) -> float:
        self._elapsed_timer.start()
        over_threshold = self._wait_for_recovery()
        elapsed_seconds = round(self._elapsed_timer.elapsed() / 1000, 3)
        if over_threshold:
            self._emit_anomaly(elapsed_seconds)
        return elapsed_seconds

    def _wait_for_recovery(self) -> bool:
        over_threshold = False
        LOGGER.debug("Normal time: %sms", self._normal_time_ms)
        while (
            recovery_time := self._time_to_process_main_thread_events()
        ) > self._normal_time_ms:
            over_threshold = True
            LOGGER.debug("Recovery time: %sms", recovery_time)
            if self._elapsed_timer.elapsed() > self._timeout_ms:
                raise TimeoutError("Recovery time exceeded timeout.")  # noqa: TRY003
            QCoreApplication.processEvents()
        return over_threshold

    def _time_to_process_main_thread_events(self) -> int:
        self._recovery_timer.start()
        for _ in range(self._process_event_count):
            QCoreApplication.processEvents()
        return self._recovery_timer.elapsed()  # ms
