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
from typing import TYPE_CHECKING, Optional

import pytest

from qgis_profiler.meters.meter import Meter, MeterAnomaly, MeterContext
from qgis_profiler.settings import ProfilerSettings

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytestqt.qtbot import QtBot


class StubMeter(Meter):
    _short_name = "stub"
    _instance: Optional["StubMeter"] = None

    @classmethod
    def get(cls) -> "StubMeter":
        if cls._instance is None:
            cls._instance = StubMeter()
        return cls._instance

    def reset_parameters(self) -> None:
        return

    def _measure(self) -> tuple[float, bool]:
        return 1.0, True


class StubClass:
    @StubMeter.monitor("foo", "bar", measure_after_call=True)
    def name_and_group_set(self, a: int, b: int) -> int:
        return a + b

    @StubMeter.monitor(name_args=["a", "b"], measure_after_call=True)
    def name_args_set(self, a: int, b: int) -> int:
        return a + b


@pytest.fixture
def meter(mock_profiler: "MagicMock") -> Iterator[Meter]:
    meter = StubMeter.get()
    yield meter
    meter.cleanup()


@pytest.fixture
def initial_context(meters_group: str):
    return MeterContext("StubMeter (stub)", meters_group)


def test_meter_should_emit_anomaly_detected(meter: Meter, qtbot: "QtBot"):
    with qtbot.waitSignal(meter.anomaly_detected, timeout=100):
        assert meter.measure() == 1.0


def test_meter_context_stack(meter: Meter, initial_context: str):
    group1 = "group1"
    group2 = "group2"

    assert meter._context_stack == []
    assert meter.current_context == initial_context

    meter.add_context("foo", group1)
    assert meter.current_context == MeterContext("foo (stub)", group1)
    meter.add_context("bar", group2)
    assert meter.current_context == MeterContext("bar (stub)", group2)
    assert meter.pop_context() == MeterContext("bar", group2)
    assert meter.current_context == MeterContext("foo (stub)", group1)
    assert meter.pop_context() == MeterContext("foo", group1)
    assert meter.current_context == initial_context


def test_meter_context_stack_with_context_manager(meter: Meter, initial_context: str):
    group1 = "group1"
    group2 = "group2"

    assert meter._context_stack == []
    assert meter.current_context == initial_context

    with meter.context("foo", group1) as context1:
        assert context1 == MeterContext("foo (stub)", group1)
        assert meter.current_context == context1
        with meter.context("bar", group2) as context2:
            assert context2 == MeterContext("bar (stub)", group2)
            assert meter.current_context == context2
        assert meter.current_context == context1
    assert meter.current_context == initial_context


@pytest.mark.parametrize(
    argnames=("method", "expected_context"),
    argvalues=[
        ("name_and_group_set", MeterContext("foo (stub)", "bar")),
        (
            "name_args_set",
            MeterContext(
                "name_args_set(a=1, b=2) (stub)", ProfilerSettings.active_group.get()
            ),
        ),
    ],
    ids=[
        "name_and_group_set",
        "name_args_set",
    ],
)
def test_monitor_decorator_should_set_context_and_measure(
    meter: Meter,
    method: str,
    expected_context: MeterContext,
    initial_context: str,
    mock_profiler: "MagicMock",
    qtbot: "QtBot",
):
    tester = StubClass()

    assert not meter.is_connected_to_profiler

    with qtbot.waitSignal(meter.anomaly_detected, timeout=100) as blocker:
        assert getattr(tester, method)(1, 2) == 3

    assert blocker.args[0] == MeterAnomaly(expected_context, duration_seconds=1.0)
    assert meter.current_context == initial_context
    assert meter.is_connected_to_profiler
    mock_profiler.add_record.assert_called_once_with(
        expected_context.name, expected_context.group, 1.0
    )


def test_monitor_decorator_should_not_do_anything_if_disabled(
    meter: Meter,
    mock_profiler: "MagicMock",
):
    tester = StubClass()
    meter.enabled = False

    assert not meter.is_connected_to_profiler
    assert tester.name_args_set(1, 2) == 3
    assert not meter.is_connected_to_profiler
    mock_profiler.add_record.assert_not_called()
