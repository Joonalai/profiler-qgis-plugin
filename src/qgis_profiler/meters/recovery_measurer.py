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
from typing import Optional

from qgis.PyQt.QtCore import QCoreApplication, QElapsedTimer

from qgis_profiler.meters.meter import Meter
from qgis_profiler.settings import ProfilerSettings

LOGGER = logging.getLogger(__name__)


class RecoveryMeasurer(Meter):
    """
    Sometimes QGIS freezes and becomes slow for a short period of
    time. This meter measures how much time it takes for QGIS to
    become fully responsive again.
    """

    _instance: Optional["RecoveryMeasurer"] = None

    def __init__(
        self,
        process_event_count: int,
        threshold_s: int,
        timeout_s: int,
    ) -> None:
        super().__init__()
        self._process_event_count = process_event_count
        self._threshold_ms = threshold_s * 1000
        self._timeout_ms = timeout_s * 1000
        self._elapsed_timer = QElapsedTimer()
        self._recovery_timer = QElapsedTimer()
        LOGGER.debug("Recovery parameters initialized: %s", self)

    def __str__(self) -> str:
        return (
            f"RecoveryMeasurer("
            f"process_event_count={self._process_event_count}, "
            f"threshold_s={self._threshold_ms / 1000},"
            f"timeout_s={self._timeout_ms / 1000}),"
        )

    @classmethod
    def get(cls) -> "RecoveryMeasurer":
        if cls._instance is None:
            cls._instance = RecoveryMeasurer(
                process_event_count=ProfilerSettings.recovery_process_event_count.get(),
                threshold_s=ProfilerSettings.recovery_threshold.get(),
                timeout_s=ProfilerSettings.recovery_timeout.get(),
            )
            cls._instance.enabled = ProfilerSettings.recovery_meter_enabled.get()
        return cls._instance

    def reset_parameters(self) -> None:
        self._process_event_count = ProfilerSettings.recovery_process_event_count.get()
        self._threshold_ms = ProfilerSettings.recovery_threshold.get() * 1000
        self._timeout_ms = ProfilerSettings.recovery_timeout.get() * 1000
        self.enabled = ProfilerSettings.recovery_meter_enabled.get()
        LOGGER.debug("Recovery parameters reset: %s", self)

    def _measure(self) -> tuple[float, bool]:
        self._elapsed_timer.start()
        over_threshold = self._wait_for_recovery()
        elapsed_seconds = round(self._elapsed_timer.elapsed() / 1000, 3)
        return elapsed_seconds, over_threshold

    def _wait_for_recovery(self) -> bool:
        over_threshold = False
        while (
            recovery_time := self._time_to_process_main_thread_events()
        ) > self._threshold_ms:
            over_threshold = True
            LOGGER.debug("Recovery time: %sms", recovery_time)
            if self._elapsed_timer.elapsed() > self._timeout_ms:
                LOGGER.warning("Recovery time exceeded timeout")
                break
            QCoreApplication.processEvents()
        return over_threshold

    def _time_to_process_main_thread_events(self) -> int:
        self._recovery_timer.start()
        for _ in range(self._process_event_count):
            QCoreApplication.processEvents()
        return self._recovery_timer.elapsed()  # ms
