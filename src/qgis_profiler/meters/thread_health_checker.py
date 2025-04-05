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
from typing import Optional

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import (
    QElapsedTimer,
    QEventLoop,
    QObject,
    QThread,
    QTimer,
    pyqtSignal,
    pyqtSlot,
)

from qgis_profiler.meters.meter import Meter
from qgis_profiler.settings import ProfilerSettings

LOGGER = logging.getLogger(__name__)


class ThreadPoller(QObject):
    poll = pyqtSignal()

    def __init__(self, poll_interval_ms: int) -> None:
        super().__init__()
        self._polling_active: bool = False
        self._elapsed_timer = QElapsedTimer()
        self._poll_interval = poll_interval_ms
        self._timer: Optional[QTimer] = None
        self._event_loop = QEventLoop(self)

    @pyqtSlot()
    def start(self) -> None:
        """Start polling."""
        LOGGER.debug("Starting thread poller")
        self._run_polling()
        self._setup_timer()
        self._event_loop.exec()

    @pyqtSlot()
    def stop(self) -> None:
        """Stop polling."""
        LOGGER.debug("Stopping thread poller")
        if self._timer:
            self._timer.stop()
        self._event_loop.exit()

    def elapsed_ms_after_last_ping(self) -> int:
        """Return elapsed milliseconds since last ping."""
        return self._elapsed_timer.elapsed()

    def set_poll_finished(self) -> None:
        """Mark polling as finished."""
        self._polling_active = False

    @pyqtSlot()
    def _run_polling(self) -> None:
        """Emit poll and restart the elapsed timer."""
        if self._polling_active:
            return
        self._polling_active = True
        self._elapsed_timer.restart()
        self.poll.emit()

    def _setup_timer(self) -> None:
        """Set up the QTimer for periodic polling."""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._run_polling)
        self._timer.start(self._poll_interval)


class MainThreadHealthChecker(Meter):
    """
    Monitors the health of the main application thread.

    Provides mechanisms to measure delays between thread pings and
    detect anomalies based on a defined threshold.
    """

    _short_name = "main_thread"
    _instance: Optional["MainThreadHealthChecker"] = None

    def __init__(self, poll_interval_s: float, threshold_s: float) -> None:
        super().__init__(supports_continuous_measurement=True)
        self._poll_interval_ms = poll_interval_s * 1000
        self._threshold_ms = threshold_s * 1000

        self._poller: Optional[ThreadPoller] = None
        self._polling_thread: Optional[QThread] = None
        self._last_delay_ms: int = 0
        LOGGER.debug("Health checker parameters initialized: %s", self)

    def __str__(self) -> str:
        return (
            f"MainThreadHealthChecker("
            f"poll_interval_s={self._poll_interval_ms / 1000}, "
            f"threshold_s={self._threshold_ms / 1000})"
        )

    @classmethod
    def get(cls) -> "MainThreadHealthChecker":
        if cls._instance is None:
            cls._instance = MainThreadHealthChecker(
                poll_interval_s=ProfilerSettings.thread_health_checker_poll_interval.get(),
                threshold_s=ProfilerSettings.thread_health_checker_threshold.get(),
            )
            cls._instance.enabled = ProfilerSettings.thread_health_checker_enabled.get()
        return cls._instance

    def reset_parameters(self) -> None:
        self._poll_interval_ms = (
            ProfilerSettings.thread_health_checker_poll_interval.get() * 1000
        )
        self._threshold_ms = (
            ProfilerSettings.thread_health_checker_threshold.get() * 1000
        )
        self.enabled = ProfilerSettings.thread_health_checker_enabled.get()
        LOGGER.debug("Health checker parameters reset: %s", self)

    def _start_measuring(self) -> bool:
        LOGGER.debug("Starting health checking")
        self._poller = ThreadPoller(int(self._poll_interval_ms))
        self._poller.poll.connect(self._on_poll_event)

        self._polling_thread = QThread(self)
        self._poller.moveToThread(self._polling_thread)

        self._polling_thread.finished.connect(self._poller.stop)
        self._polling_thread.finished.connect(self._poller.deleteLater)
        self._polling_thread.finished.connect(self._polling_thread.deleteLater)
        self._polling_thread.started.connect(self._poller.start)
        self._polling_thread.start()
        return True

    def _stop_measuring(self) -> None:
        LOGGER.debug("Stopping health checking")
        if self._poller:
            self._poller.poll.disconnect(self._on_poll_event)
        if self._polling_thread and self._polling_thread.isRunning():
            self._polling_thread.quit()
            self._polling_thread.wait()
        self._polling_thread = None
        self._poller = None

    def _measure(self) -> tuple[float, bool]:
        """
        Measure the delay between thread poll and main thread response.

        :return: the last delay in milliseconds and whether
        it exceeded the threshold.
        """
        if self._poller:
            return self._last_delay_ms / 1000, self._last_delay_ms > self._threshold_ms

        self._last_delay_ms = 0
        self.start_measuring()
        t = time.time()
        while (
            self._last_delay_ms == 0
            and time.time() - t
            < ProfilerSettings.thread_health_checker_poll_interval.get() * 2
        ):
            QgsApplication.processEvents()
        self.cleanup()
        return self._last_delay_ms / 1000, self._last_delay_ms > self._threshold_ms

    @pyqtSlot()
    def _on_poll_event(self) -> None:
        """Handle poll events."""
        if not self._poller:
            # Should not be possible
            return
        elapsed_ms = self._poller.elapsed_ms_after_last_ping()
        if elapsed_ms > self._threshold_ms:
            LOGGER.debug("Took too long %s ms", elapsed_ms)
            self._emit_anomaly(round(elapsed_ms / 1000, 3))
        self._poller.set_poll_finished()
        self._last_delay_ms = elapsed_ms
