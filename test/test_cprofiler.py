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
from pathlib import Path
from textwrap import dedent

import pytest

from profiler_test_utils.decorator_utils import (
    call_cprofile_decorated_function,
    get_cprofile_decorated_plugin_class,
)
from qgis_profiler.cprofiler import ProfilerEntry, QCProfiler

LOGGER = logging.getLogger(__name__)


class Class:
    # @profile
    def foo(self, a: int, b: int) -> int:
        self.sleep(0.1)
        return a + b + self.bar(a, b)

    # @profile
    def bar(self, a: int, b: int) -> int:
        self.sleep(0.2)
        if b == 0:
            return a + self.foo(a, 1)
        return a + b

    # @profile
    def sleep(self, amount: float) -> None:
        time.sleep(amount)


@pytest.fixture
def cprofiler() -> QCProfiler:
    return QCProfiler()


@pytest.fixture
def sample_text(default_group: str) -> str:
    qgis_profiler_log = """
    Plugins
    - _import: 0.0
    - foo: 0.3
    -- sleep: 0.1
    -- bar: 0.2
    --- sleep: 0.2
    - bar: 0.5
    -- sleep: 0.2
    -- foo: 0.3
    --- sleep: 0.1
    --- bar: 0.2
    ---- sleep: 0.2
    """
    return dedent(qgis_profiler_log).strip()


@pytest.fixture
def parsed_profiler_entries(sample_text: str) -> list[ProfilerEntry]:
    return ProfilerEntry.parse_from_qgis_profiler_text(sample_text)


def test_parse_profile_entries_from_qgis_profiler_text(
    parsed_profiler_entries: list[ProfilerEntry],
):
    assert parsed_profiler_entries == [
        ProfilerEntry(
            code="_import",
            callcount=1,
            inlinetime=0.0,
            reccallcount=0,
            totaltime=0.0,
            calls=[],
        ),
        ProfilerEntry(
            code="foo",
            callcount=2,
            inlinetime=0.0,
            reccallcount=0,
            totaltime=0.6,
            calls=[
                ProfilerEntry(
                    code="sleep",
                    callcount=2,
                    inlinetime=0.2,
                    reccallcount=0,
                    totaltime=0.2,
                    calls=[],
                ),
                ProfilerEntry(
                    code="bar",
                    callcount=2,
                    inlinetime=0.0,
                    reccallcount=0,
                    totaltime=0.4,
                    calls=[],
                ),
            ],
        ),
        ProfilerEntry(
            code="sleep",
            callcount=5,
            inlinetime=0.8,
            reccallcount=0,
            totaltime=0.8,
            calls=[],
        ),
        ProfilerEntry(
            code="bar",
            callcount=3,
            inlinetime=0.0,
            reccallcount=1,
            totaltime=0.9,
            calls=[
                ProfilerEntry(
                    code="sleep",
                    callcount=3,
                    inlinetime=0.6,
                    reccallcount=0,
                    totaltime=0.6,
                    calls=[],
                ),
                ProfilerEntry(
                    code="foo",
                    callcount=1,
                    inlinetime=0.0,
                    reccallcount=0,
                    totaltime=0.3,
                    calls=[],
                ),
            ],
        ),
    ]


def test_cprofiler_should_generate_stat_report_from_qgis_profiler_text(
    cprofiler: QCProfiler, sample_text: str
):
    with cprofiler.qgis_profiler_data(sample_text):
        report = cprofiler.get_stat_report("cumtime")
    LOGGER.debug("\n%s", report)
    assert (
        report.strip()
        == """\
11 function calls (10 primitive calls) in 0.800 seconds

   Ordered by: cumulative time

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
      3/2    0.000    0.000    0.900    0.450 bar
        5    0.800    0.160    0.800    0.160 sleep
        2    0.000    0.000    0.600    0.300 foo
        1    0.000    0.000    0.000    0.000 _import"""
    )


def test_cprofiler_report_should_be_trimmed(cprofiler: QCProfiler, sample_text: str):
    with cprofiler.qgis_profiler_data(sample_text):
        report = cprofiler.get_stat_report("cumtime", max_line_count=2, trim_zeros=True)
    LOGGER.debug("\n%s", report)
    assert (
        report.strip()
        == """\
11 function calls (10 primitive calls) in 0.800 seconds

   Ordered by: cumulative time

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
      3/2    0.000    0.000    0.900    0.450 bar
        5    0.800    0.160    0.800    0.160 sleep"""
    )


def test_cprofiler_should_profile_normally(cprofiler: QCProfiler, sample_text: str):
    cprofiler.enable(builtins=False)
    assert cprofiler.is_profiling()
    f = Class()
    f.foo(1, 2)
    f.bar(2, 0)
    cprofiler.disable()
    assert not cprofiler.is_profiling()
    entries = ProfilerEntry.from_cprofiler(cprofiler)

    # It is rather challenging to compare the
    # results directly since times might differ greatly
    names = {entry.code for entry in entries}
    assert names == {"bar", "foo", "is_profiling", "disable", "_import", "sleep"}
    report = cprofiler.get_stat_report("cumtime")
    LOGGER.info(report)
    assert "bar" in report
    assert "sleep" in report
    assert "foo" in report
    assert "_import" in report


def test_cprofile_decorator(tmp_path: Path):
    # Arrange
    result_file = tmp_path / "result.prof"
    assert not result_file.exists()

    # Act
    call_cprofile_decorated_function(result_file)

    # Assert
    assert result_file.exists()
    assert result_file.stat().st_size > 0


def test_cprofile_plugin_decorator(tmp_path: Path):
    # Arrange
    result_file = tmp_path / "result.prof"
    assert not result_file.exists()

    # Act
    plugin = get_cprofile_decorated_plugin_class(result_file)
    plugin.initGui()
    plugin.unload()

    # Assert
    assert result_file.exists()
    assert result_file.stat().st_size > 0
