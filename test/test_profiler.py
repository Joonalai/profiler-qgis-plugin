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
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest
from qgis.core import QgsApplication

from qgis_profiler.decorators import profile, profile_recovery_time
from qgis_profiler.profiler import ProfilerResult, RecoveryMeasurer, profiler
from qgis_profiler.settings import ProfilerSettings

if TYPE_CHECKING:
    from pytest_subtests import SubTests
    from pytestqt.qtbot import QtBot

LOGGER = logging.getLogger(__name__)


@pytest.fixture
def sample_text(default_group: str) -> str:
    return dedent(
        """
    group_line_which_wont_be_parsed
    - Task A: 1.25
    -- Subtask A1: 0.50
    --- SubSubtask A2: 0.60
    -- Subtask A2: 0.75
    - Task B: 2.00
    - Task C: 3.50
    """
    ).strip()


def recovery_measurer() -> RecoveryMeasurer:
    return RecoveryMeasurer(
        process_event_count=ProfilerSettings.process_event_count.get(),
        normal_time_s=ProfilerSettings.normal_time.get(),
        timeout_s=ProfilerSettings.timeout.get(),
    )


def test_profiler_results_should_be_considered_equal():
    result1 = ProfilerResult("Task A", "group", 1.25)
    result2 = ProfilerResult("Task A", "group", 1.251)
    assert result1 == result2


def test_profiler_results_should_not_be_considered_equal():
    result1 = ProfilerResult("Task A", "group", 1.25)
    result2 = ProfilerResult("Task A", "group", 1.26)
    assert result1 != result2


def test_profiler_result_parsing(sample_text: str, default_group: str):
    results = ProfilerResult.parse_from_text(sample_text, default_group)
    assert results == [
        ProfilerResult(
            name="Task A",
            group=default_group,
            duration=1.25,
            children=[
                ProfilerResult(
                    name="Subtask A1",
                    group=default_group,
                    duration=0.5,
                    children=[
                        ProfilerResult(
                            name="SubSubtask A2",
                            group=default_group,
                            duration=0.6,
                            children=[],
                        )
                    ],
                ),
                ProfilerResult(
                    name="Subtask A2", group=default_group, duration=0.75, children=[]
                ),
            ],
        ),
        ProfilerResult(name="Task B", group=default_group, duration=2.0, children=[]),
        ProfilerResult(name="Task C", group=default_group, duration=3.5, children=[]),
    ]


def test_profiler_context_manager(qtbot: "QtBot", default_group: str):
    def some_function():
        with profiler.profile("some_function"):
            qtbot.wait(10)

    some_function()
    data = profiler.get_profiler_data("some_function")
    assert data == [
        ProfilerResult("some_function", ProfilerSettings.active_group.get(), 0.01)
    ]


@pytest.mark.xfail(reason="Test is not done yet")
def test_recovery_measurer(default_group: str, recovery_measurer: RecoveryMeasurer):
    assert recovery_measurer.measure_recovery_time() == pytest.approx(0.1, abs=1e-1)


@pytest.mark.xfail(reason="Test is not done yet")
def test_profile_recovery_time(qtbot: "QtBot"):
    @profile_recovery_time()
    def some_function():
        qtbot.wait(10)

    some_function()
    data = profiler.get_profiler_data("some_function (recovery)")
    assert data == [
        ProfilerResult("some_function", ProfilerSettings.active_group.get(), 0.01)
    ]


def test_profile_decorator_should_profile_method(
    qtbot: "QtBot", subtests: "SubTests", default_group: str
):
    def _add(a: int, b: int = 2) -> int:
        qtbot.wait(10)
        return a + b

    class Class:
        @profile()
        def add(self, a: int, b: int = 2) -> int:
            return _add(a, b)

        @profile("Add numbers")
        def add_with_name_arg(self, a: int, b: int = 2) -> int:
            return _add(a, b)

        @profile()
        def add_complex(self, a: int, b: int = 2) -> int:
            qtbot.wait(10)
            return self.add(a, b) + self.add_with_name_arg(a, b)

        @staticmethod
        @profile()
        def static_add(a: int, b: int = 2) -> int:
            return _add(a, b)

    instance = Class()

    expected_time = 0.01
    with subtests.test("should profile method with name arg"):
        assert instance.add_with_name_arg(1, 2) == 3
        data = profiler.get_profiler_data("Add numbers")
        assert data == [ProfilerResult("Add numbers", default_group, expected_time)]
    with subtests.test("should profile method without name arg"):
        assert instance.add(1, 2) == 3
        data = profiler.get_profiler_data("add")
        assert data == [ProfilerResult("add", default_group, expected_time)]
    with subtests.test("should profile static method"):
        assert instance.static_add(1, 2) == 3
        data = profiler.get_profiler_data("static_add")
        assert data == [ProfilerResult("static_add", default_group, expected_time)]

    with subtests.test("should profile complex method"):
        assert instance.add_complex(1, 2) == 6
        data = profiler.get_profiler_data("add_complex")
        assert data == [
            ProfilerResult(
                "add_complex",
                default_group,
                expected_time * 3,
                children=[
                    ProfilerResult(
                        name="add", group=default_group, duration=0.01, children=[]
                    ),
                    ProfilerResult(
                        name="Add numbers",
                        group=default_group,
                        duration=0.01,
                        children=[],
                    ),
                ],
            ),
        ]
    with subtests.test("all add events should be found"):
        data = profiler.get_profiler_data("add")
        assert data == [
            ProfilerResult(name="add", group=default_group, duration=0.01, children=[]),
            ProfilerResult(name="add", group=default_group, duration=0.01, children=[]),
        ]
    with subtests.test("all events should be found"):
        data = profiler.get_profiler_data()
        assert data == [
            ProfilerResult(
                name="Add numbers", group=default_group, duration=0.01, children=[]
            ),
            ProfilerResult(name="add", group=default_group, duration=0.01, children=[]),
            ProfilerResult(
                name="static_add", group=default_group, duration=0.01, children=[]
            ),
            ProfilerResult(
                name="add_complex",
                group=default_group,
                duration=0.031,
                children=[
                    ProfilerResult(
                        name="add", group=default_group, duration=0.01, children=[]
                    ),
                    ProfilerResult(
                        name="Add numbers",
                        group=default_group,
                        duration=0.01,
                        children=[],
                    ),
                ],
            ),
        ]
    LOGGER.info(QgsApplication.profiler().asText(ProfilerSettings.active_group.get()))
