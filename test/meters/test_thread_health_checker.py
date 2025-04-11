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

from qgis_profiler.meters.meter import MeterAnomaly, MeterContext
from qgis_profiler.meters.thread_health_checker import (
    MainThreadHealthChecker,
)

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytestqt.qtbot import QtBot

    from profiler_test_utils.decorator_utils import DecoratorTester


@pytest.fixture
def thread_health_checker(
    mock_profiler: "MagicMock",
) -> Iterator[MainThreadHealthChecker]:
    """Fixture to create and return a MainThreadChecker instance."""
    checker = MainThreadHealthChecker.get()
    checker._poll_interval_ms = 10
    checker._threshold_ms = 90
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
    meters_group: str,
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
    assert anomaly.context == MeterContext(
        "MainThreadHealthChecker (main_thread)", meters_group
    )
    assert anomaly.duration_seconds == pytest.approx(0.2, rel=0.1)

    # single-shot measure should give the latest delay
    assert (
        thread_health_checker.measure() == thread_health_checker._last_delay_ms / 1000
    )


def test_health_checker_measure_should_poll_blocking(
    thread_health_checker: MainThreadHealthChecker,
    qtbot: "QtBot",
):
    duration = thread_health_checker.measure()
    assert duration == pytest.approx(0.1, abs=1e-1)


@pytest.mark.parametrize(
    "method", ["monitor_thread_health", "monitor_thread_health_without_parenthesis"]
)
def test_monitor_main_thread_health_decorator_should_profile(
    thread_health_checker: MainThreadHealthChecker,
    default_group: str,
    decorator_tester: "DecoratorTester",
    mock_profiler: "MagicMock",
    qtbot: "QtBot",
    method: str,
):
    # Act
    with qtbot.waitSignal(thread_health_checker.anomaly_detected, timeout=200):
        getattr(decorator_tester, method)()

    # Assert
    mock_profiler.add_record.assert_called_once_with(
        f"{method} (main_thread)",
        default_group,
        pytest.approx(0.1, abs=1e-1),
    )
    assert thread_health_checker.is_measuring
