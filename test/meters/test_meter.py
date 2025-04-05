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
from typing import TYPE_CHECKING, Optional

import pytest

from qgis_profiler.meters.meter import Meter

if TYPE_CHECKING:
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


@pytest.fixture
def meter() -> Meter:
    return StubMeter.get()


def test_meter_should_emit_anomaly_detected(meter: Meter, qtbot: "QtBot"):
    with qtbot.waitSignal(meter.anomaly_detected, timeout=100):
        assert meter.measure() == 1.0


def test_meter_context_stack(meter: Meter):
    assert meter._context_stack == []
    assert meter.current_context == "StubMeter (stub)"

    meter.add_context("foo")
    assert meter.current_context == "foo (stub)"
    meter.add_context("bar")
    assert meter.current_context == "bar (stub)"
    assert meter.pop_context() == "bar"
    assert meter.current_context == "foo (stub)"
    assert meter.pop_context() == "foo"
    assert meter.current_context == "StubMeter (stub)"


def test_meter_context_stack_with_context_manager(meter: Meter):
    assert meter._context_stack == []
    assert meter.current_context == "StubMeter (stub)"

    with meter.context("foo") as context:
        assert context == "foo (stub)"
        with meter.context("bar") as context2:
            assert context2 == "bar (stub)"
            assert meter.current_context == "bar (stub)"
        assert meter.current_context == "foo (stub)"
    assert meter.current_context == "StubMeter (stub)"
