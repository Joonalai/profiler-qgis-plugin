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
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from profiler_test_utils import utils
from profiler_test_utils.decorator_utils import (
    EXPECTED_TIME,
    EXTRA_GROUP,
    ClassDecoratorTester,
    DecoratorTester,
)
from qgis_profiler.cprofiler import QCProfiler
from qgis_profiler.profiler import (
    ProfilerResult,
    ProfilerWrapper,
)
from qgis_profiler.settings import Settings

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from pytestqt.qtbot import QtBot


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


def test_profiler_start_and_end(
    profiler: "ProfilerWrapper", qtbot: "QtBot", default_group: str
):
    # Act
    event_id = profiler.start("test", default_group)
    qtbot.wait(10)
    event_id2 = profiler.end(default_group)

    # Assert
    assert event_id
    assert event_id == event_id2

    data = profiler.get_profiler_data("test")
    assert data == [ProfilerResult("test", Settings.active_group.get(), 0.01)]
    assert profiler.get_event_time(event_id) == pytest.approx(0.0, abs=1e-1)


def test_profiler_add_record(
    profiler: "ProfilerWrapper", qtbot: "QtBot", default_group: str
):
    # Act
    event_id = profiler.add_record("added_record", default_group, 0.01)
    qtbot.wait(10)
    profiler.end(default_group)

    # Assert
    assert event_id

    data = profiler.get_profiler_data("added_record")
    assert data == [ProfilerResult("added_record", Settings.active_group.get(), 0.01)]
    assert profiler.get_event_time(event_id) == pytest.approx(0.0, abs=1e-1)


def test_profiler_context_manager(
    profiler: "ProfilerWrapper", qtbot: "QtBot", default_group: str
):
    # Arrange
    def some_function():
        with profiler.profile("some_function") as event_id:
            qtbot.wait(10)
        return event_id

    # Act
    event_id = some_function()

    # Assert
    assert event_id
    data = profiler.get_profiler_data("some_function")
    assert data == [ProfilerResult("some_function", Settings.active_group.get(), 0.01)]
    assert profiler.get_event_time(event_id) == pytest.approx(0.01, abs=1e-1)


@pytest.mark.parametrize(
    argnames=("method", "method_result", "expected_name", "expected_data"),
    argvalues=[
        (
            "add_with_name_kwarg",
            3,
            "Add numbers",
            [ProfilerResult("Add numbers", "", EXPECTED_TIME)],
        ),
        (
            "add",
            3,
            "add",
            [ProfilerResult("add", "", EXPECTED_TIME)],
        ),
        (
            "static_add",
            3,
            "static_add",
            [ProfilerResult("static_add", "", EXPECTED_TIME)],
        ),
        (
            "add_complex",
            6,
            "add_complex",
            [
                ProfilerResult(
                    "add_complex",
                    "",
                    EXPECTED_TIME * 3,
                    children=[
                        ProfilerResult(
                            name="add", group="", duration=EXPECTED_TIME, children=[]
                        ),
                        ProfilerResult(
                            name="Add numbers",
                            group="",
                            duration=EXPECTED_TIME,
                            children=[],
                        ),
                    ],
                ),
            ],
        ),
        (
            "add_with_event_args",
            3,
            "add_with_event_args(a=1)",
            [ProfilerResult("add_with_event_args(a=1)", "", EXPECTED_TIME)],
        ),
    ],
    ids=[
        "profile method with name arg",
        "profile method without name arg",
        "profile static method",
        "profile complex method",
        "profile method with event args",
    ],
)
@pytest.mark.usefixtures("log_profiler_data")
def test_profile_decorator_should_profile_method(
    profiler: "ProfilerWrapper",
    default_group: str,
    decorator_tester: DecoratorTester,
    method: str,
    method_result: int,
    expected_name: str,
    expected_data: list[ProfilerResult],
):
    assert getattr(decorator_tester, method)(1, 2) == method_result
    assert default_group in profiler.groups
    data = profiler.get_profiler_data(expected_name)
    assert data == utils.profiler_data_with_group(default_group, expected_data)


@pytest.mark.parametrize(
    argnames=("method", "method_result", "expected_name", "expected_data"),
    argvalues=[
        (
            "add",
            3,
            "add",
            [ProfilerResult("add", "", EXPECTED_TIME)],
        ),
        (
            "add_with_event_args",
            3,
            "add_with_event_args(a=1, b=2)",
            [ProfilerResult("add_with_event_args(a=1, b=2)", "", EXPECTED_TIME)],
        ),
        (
            "static_add",
            3,
            "static_add",
            [ProfilerResult("static_add", "", EXPECTED_TIME)],
        ),
        (
            "classmethod_add",
            3,
            "classmethod_add",
            [ProfilerResult("classmethod_add", "", EXPECTED_TIME)],
        ),
        (
            "add_complex",
            6,
            "add_complex",
            [
                ProfilerResult(
                    "add_complex",
                    "",
                    EXPECTED_TIME * 3,
                    children=[
                        ProfilerResult(
                            name="add", group="", duration=EXPECTED_TIME, children=[]
                        ),
                        ProfilerResult(
                            name="add",
                            group="",
                            duration=EXPECTED_TIME,
                            children=[],
                        ),
                    ],
                ),
            ],
        ),
        (
            "add_excluded",
            3,
            "add_excluded",
            None,
        ),
        (
            "static_add_excluded",
            3,
            "static_add_excluded",
            None,
        ),
        (
            "classmethod_add_excluded",
            3,
            "classmethod_add_excluded",
            None,
        ),
    ],
    ids=[
        "auto profile method",
        "auto profile method with event args",
        "auto profile static method",
        "auto profile class method",
        "auto profile complex method",
        "exclude method",
        "exclude static method",
        "exclude class method",
    ],
)
@pytest.mark.usefixtures("log_profiler_data")
def test_profile_class_decorator_should_profile_class(
    profiler: "ProfilerWrapper",
    default_group: str,
    class_decorator_tester: ClassDecoratorTester,
    method: str,
    method_result: int,
    expected_name: str,
    expected_data: list[ProfilerResult],
):
    assert getattr(class_decorator_tester, method)(1, 2) == method_result
    assert default_group in profiler.groups
    data = profiler.get_profiler_data(expected_name)
    if expected_data is None:
        assert not data
    else:
        assert data == utils.profiler_data_with_group(default_group, expected_data)


def test_profile_decorator_should_profile_method_with_group_kwarg(
    profiler: "ProfilerWrapper",
    decorator_tester: DecoratorTester,
):
    assert decorator_tester.add_with_group_kwarg(1, 2) == 3
    assert EXTRA_GROUP in profiler.groups

    # Wrong group
    assert not profiler.get_profiler_data("add_with_group_kwarg")

    # Correct group
    data = profiler.get_profiler_data("add_with_group_kwarg", EXTRA_GROUP)
    assert data == [ProfilerResult("add_with_group_kwarg", EXTRA_GROUP, EXPECTED_TIME)]


def test_profile_decorator_should_not_profile_if_profiling_is_disabled(
    profiler: "ProfilerWrapper",
    decorator_tester: DecoratorTester,
    mocker: "MockerFixture",
):
    # Arrange
    mock_settings = mocker.patch.object(Settings, "get_with_cache", return_value=False)
    # Act
    assert decorator_tester.add(1, 2) == 3
    # Assert
    mock_settings.assert_called_once()
    assert not profiler._profiler_events


def test_save_profiler_results_as_prof_file_with_valid_inputs(
    profiler: "ProfilerWrapper",
    mocker: "MockerFixture",
    decorator_tester: DecoratorTester,
) -> None:
    m_dump_stats = mocker.patch.object(QCProfiler, "dump_stats")

    assert decorator_tester.add_with_group_kwarg(1, 2) == 3

    path = Path("file.prof")
    profiler.save_profiler_results_as_prof_file("test_group", path)
    m_dump_stats.assert_called_once_with(path)
