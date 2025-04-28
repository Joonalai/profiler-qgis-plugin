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
from pathlib import Path

from profiler_test_utils import utils
from qgis_profiler.decorators import (
    cprofile,
    cprofile_plugin,
    profile,
    profile_class,
)
from qgis_profiler.meters.thread_health_checker import MainThreadHealthChecker
from qgis_profiler.utils import QgisPluginType

EXTRA_GROUP = "New group"
EXPECTED_TIME = 0.01


class DecoratorTester:
    @profile
    def add(self, a: int, b: int) -> int:
        return _add(a, b)

    @MainThreadHealthChecker.monitor()
    def monitor_thread_health(self) -> None:
        time.sleep(0.1)

    @MainThreadHealthChecker.monitor
    def monitor_thread_health_without_parenthesis(self) -> None:
        time.sleep(0.1)

    @profile(name="Add numbers")
    def add_with_name_kwarg(self, a: int, b: int) -> int:
        return _add(a, b)

    @profile(event_args=["a"])
    def add_with_event_args(self, a: int, b: int) -> int:
        return _add(a, b)

    @profile(group=EXTRA_GROUP)
    def add_with_group_kwarg(self, a: int, b: int) -> int:
        return _add(a, b)

    @profile
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


def call_cprofile_decorated_function(output_file_path: Path) -> None:
    @cprofile(output_file_path=output_file_path)
    def decorated_function() -> None:
        utils.wait(int(EXPECTED_TIME * 1000))
        _add(1, 2)

    decorated_function()


def get_cprofile_decorated_plugin_class(output_file_path: Path) -> QgisPluginType:
    @cprofile_plugin(output_file_path=output_file_path)
    class PluginDecoratorTester:
        def initGui(self) -> None:  # noqa: N802
            utils.wait(int(EXPECTED_TIME * 1000))

        def unload(self) -> None:
            utils.wait(int(EXPECTED_TIME * 1000))
            utils.wait(int(EXPECTED_TIME * 1000))

    # Profiling is started right away
    return PluginDecoratorTester()


def _add(a: int, b: int = 2) -> int:
    utils.wait(int(EXPECTED_TIME * 1000))
    return a + b
