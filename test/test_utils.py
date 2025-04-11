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
from functools import wraps
from typing import Any, Callable

import pytest

from qgis_profiler.utils import parse_arguments


def empty_decorator(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Callable:
        return func(*args, **kwargs)

    return wrapper


class StubClass:
    var = 1

    def __init__(self) -> None:
        self._val = 2

    def method(self, a: int, b: int = 3) -> None: ...

    @empty_decorator
    def decorated(self, a: int, b: int = 3) -> None: ...


@pytest.mark.parametrize(
    argnames=("function", "event_args", "args", "kwargs", "expected"),
    argvalues=[
        (StubClass().method, ["a", "b"], [1, 2], None, "(a=1, b=2)"),
        (StubClass().method, ["a"], [10], {"b": 20}, "(a=10)"),
        (StubClass().method, ["b"], [], {}, "(b=3)"),
        (StubClass().method, ["c"], [40], {}, "()"),
        (StubClass().method, ["a", "b"], [], {"a": 50, "b": 60}, "(a=50, b=60)"),
        (StubClass().method, [], [1, 2], {}, "()"),
        (StubClass().method, ["self.var", "self._val"], None, None, "(var=1, _val=2)"),
        (StubClass().decorated, ["a", "b"], [1, 2], None, "(a=1, b=2)"),
    ],
    ids=[
        "both_positional_arguments",
        "one_positional_one_keyword",
        "default_argument",
        "non_existent_argument",
        "all_keyword_arguments",
        "empty_event_args",
        "object_attributes",
        "decorated_method",
    ],
)
def test_parse_arguments_with_method(
    function: Callable, event_args: list[str], args: list, kwargs: dict, expected: str
) -> None:
    assert parse_arguments(function, event_args, args, kwargs) == expected


@pytest.mark.parametrize(
    argnames=("function", "event_args", "args", "kwargs", "expected"),
    argvalues=[
        (lambda a, b, c: None, ["a", "b"], [1, 2, 3], {}, "(a=1, b=2)"),
        (lambda x, y, z: None, ["x", "z"], [4], {"y": 5, "z": 6}, "(x=4, z=6)"),
        (lambda foo, bar: None, ["baz"], [10, 20], {}, "()"),
        (lambda a, b: None, [], [100, 200], {}, "()"),
        (lambda x, y: None, ["x", "y"], [], {}, "()"),
        (lambda x, y=None: None, ["x", "y"], [], {}, "(y=None)"),
        (lambda a, b, c: None, ["a", "c"], [1], {"b": 2, "c": 3}, "(a=1, c=3)"),
    ],
    ids=[
        "positional_arguments",
        "keyword_arguments",
        "non_existent_argument",
        "empty_event_args",
        "no_arguments_passed",
        "default_argument",
        "mixed_args_and_kwargs",
    ],
)
def test_parse_arguments_with_function(
    function: Callable, event_args: list[str], args: list, kwargs: dict, expected: str
) -> None:
    assert parse_arguments(function, event_args, args, kwargs) == expected
