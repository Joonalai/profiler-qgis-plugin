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

from qgis.PyQt.QtCore import QCoreApplication, QElapsedTimer, QObject

LOGGER = logging.getLogger(__name__)


class RecoveryMeasurer(QObject):
    """A meter for measuring the recovery time of an operation."""

    def __init__(
        self,
        process_event_count: int,
        normal_time_s: int,
        timeout_s: int,
    ) -> None:
        super().__init__()
        self._process_event_count = process_event_count
        self._normal_time_ms = normal_time_s * 1000
        self._timeout_ms = timeout_s * 1000
        self._timer = QElapsedTimer()
        self._recovery_timer = QElapsedTimer()

    def measure_recovery_time(self) -> float:
        """Measure the recovery time of an operation."""
        self._timer.start()
        LOGGER.debug("Normal time: %sms", self._normal_time_ms)
        while (t := self._measure()) > self._normal_time_ms:
            LOGGER.debug("Recovery time: %sms", t)
            if self._timer.elapsed() > self._timeout_ms:
                raise TimeoutError("Recovery time exceeded timeout.")  # noqa: TRY003
            QCoreApplication.processEvents()
        return round(self._timer.elapsed() / 1000, 3)

    def _measure(self) -> int:
        self._recovery_timer.start()
        for _ in range(self._process_event_count):
            QCoreApplication.processEvents()
        return self._recovery_timer.elapsed()  # ms
