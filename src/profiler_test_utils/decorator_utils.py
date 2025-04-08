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

from profiler_test_utils import utils
from qgis_profiler.decorators import profile, profile_class, profile_recovery_time

EXTRA_GROUP = "New group"
EXPECTED_TIME = 0.01


class DecoratorTester:
    @profile()
    def add(self, a: int, b: int) -> int:
        return _add(a, b)

    @profile()
    @profile_recovery_time()
    def add_and_profile_recovery(self, a: int, b: int) -> int:
        return _add(a, b)

    @profile_recovery_time()
    def just_profile_recovery(self) -> None:
        return

    @profile(name="Add numbers")
    def add_with_name_kwarg(self, a: int, b: int) -> int:
        return _add(a, b)

    @profile(event_args=["a"])
    def add_with_event_args(self, a: int, b: int) -> int:
        return _add(a, b)

    @profile(group=EXTRA_GROUP)
    def add_with_group_kwarg(self, a: int, b: int) -> int:
        return _add(a, b)

    @profile()
    def add_complex(self, a: int, b: int) -> int:
        utils.wait(int(EXPECTED_TIME * 1000))
        return self.add(a, b) + self.add_with_name_kwarg(a, b)

    @staticmethod
    @profile()
    def static_add(a: int, b: int = 2) -> int:
        return _add(a, b)


@profile_class(
    exclude=["add_excluded", "static_add_excluded", "classmethod_add_excluded"]
)
class ClassDecoratorTester:
    def add(self, a: int, b: int) -> int:
        return _add(a, b)

    def add_complex(self, a: int, b: int) -> int:
        utils.wait(int(EXPECTED_TIME * 1000))
        return self.add(a, b) + self.add(a, b)

    @profile(event_args=["a", "b"])
    def add_with_event_args(self, a: int, b: int) -> int:
        return _add(a, b)

    @staticmethod
    def static_add(a: int, b: int) -> int:
        return _add(a, b)

    @classmethod
    def classmethod_add(cls, a: int, b: int) -> int:
        return _add(a, b)

    def add_excluded(self, a: int, b: int) -> int:
        return _add(a, b)

    @staticmethod
    def static_add_excluded(a: int, b: int) -> int:
        return _add(a, b)

    @classmethod
    def classmethod_add_excluded(cls, a: int, b: int) -> int:
        return _add(a, b)


def _add(a: int, b: int = 2) -> int:
    utils.wait(int(EXPECTED_TIME * 1000))
    return a + b
