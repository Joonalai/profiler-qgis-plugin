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

import time
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest

from qgis_profiler.meters.meter import MeterAnomaly
from qgis_profiler.meters.thread_health_checker import (
    MainThreadHealthChecker,
)

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


@pytest.fixture
def thread_health_checker() -> Iterator[MainThreadHealthChecker]:
    """Fixture to create and return a MainThreadChecker instance."""
    checker = MainThreadHealthChecker(0.010, 0.090)
    yield checker
    checker.cleanup()  # Ensure the checker is stopped after the test
    assert checker.is_measuring is False


def test_thread_poller_should_start_polling(
    thread_health_checker: MainThreadHealthChecker, qtbot: "QtBot"
):
    assert not thread_health_checker.is_measuring

    thread_health_checker.start_measuring()

    assert thread_health_checker.is_measuring
    assert thread_health_checker._poller
    with qtbot.waitSignal(thread_health_checker._poller.poll, timeout=100):
        """Poll should be called once"""

    with qtbot.waitSignal(thread_health_checker._poller.poll, timeout=100):
        """Wait again, timer should work"""


def test_health_checker_should_emit_anomaly_on_thread_block(
    thread_health_checker: MainThreadHealthChecker,
    qtbot: "QtBot",
):
    # Arrange
    thread_health_checker.start_measuring()

    # Act
    with qtbot.waitSignal(
        thread_health_checker.anomaly_detected, timeout=200
    ) as signal_blocker:
        time.sleep(0.2)

    # Assert
    anomaly = signal_blocker.args[0]
    assert isinstance(anomaly, MeterAnomaly)
    assert anomaly.name == "MainThreadHealthChecker"
    assert anomaly.duration_seconds == pytest.approx(0.2, rel=0.1)
