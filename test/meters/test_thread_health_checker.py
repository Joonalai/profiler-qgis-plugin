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

from profiler_test_utils.decorator_utils import DecoratorTester
from qgis_profiler.meters.meter import MeterAnomaly
from qgis_profiler.meters.thread_health_checker import (
    MainThreadHealthChecker,
)
from qgis_profiler.settings import ProfilerSettings

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture
    from pytestqt.qtbot import QtBot


@pytest.fixture
def thread_health_checker() -> Iterator[MainThreadHealthChecker]:
    """Fixture to create and return a MainThreadChecker instance."""
    checker = MainThreadHealthChecker.get()
    checker._poll_interval_ms = 10
    checker._threshold_ms = 90
    yield checker
    checker.cleanup()  # Ensure the checker is stopped after the test


def test_thread_poller_should_start_polling(
    thread_health_checker: MainThreadHealthChecker, qtbot: "QtBot"
):
    thread_health_checker.start_measuring()
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
    assert anomaly.name == "MainThreadHealthChecker (main_thread)"
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


@pytest.mark.usefixtures("thread_health_checker")
def test_monitor_main_thread_health_decorator_should_profile(
    decorator_tester: "DecoratorTester",
    mock_profiler: "MagicMock",
):
    # Act
    decorator_tester.monitor_thread_health()
    # Assert
    mock_profiler.add_record.assert_called_once_with(
        "monitor_thread_health (main_thread)", "Plugins", pytest.approx(0.1, abs=1e-1)
    )


@pytest.mark.usefixtures("thread_health_checker")
def test_monitor_main_thread_health_should_not_profile_if_profiling_is_disabled(
    decorator_tester: DecoratorTester,
    mocker: "MockerFixture",
    mock_profiler: "MagicMock",
):
    # Arrange
    mock_settings = mocker.patch.object(
        ProfilerSettings, "get_with_cache", return_value=False
    )
    # Act
    decorator_tester.monitor_thread_health()
    # Assert
    mock_settings.assert_called_once()
    mock_profiler.add_record.assert_not_called()
