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
from typing import TYPE_CHECKING

import pytest

from profiler_test_utils.decorator_utils import DecoratorTester
from qgis_profiler.decorators import profile_recovery_time
from qgis_profiler.meters.recovery_measurer import RecoveryMeasurer
from qgis_profiler.profiler import ProfilerResult, ProfilerWrapper
from qgis_profiler.settings import ProfilerSettings

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from pytestqt.qtbot import QtBot


@pytest.fixture
def recovery_measurer() -> RecoveryMeasurer:
    return RecoveryMeasurer(
        process_event_count=ProfilerSettings.process_event_count.get(),
        normal_time_s=ProfilerSettings.normal_time.get(),
        timeout_s=ProfilerSettings.timeout.get(),
        context="test",
    )


def test_profile_recovery_time_decorator_should_not_profile_if_profiling_is_disabled(
    profiler: "ProfilerWrapper",
    decorator_tester: DecoratorTester,
    mocker: "MockerFixture",
):
    # Arrange
    mock_settings = mocker.patch.object(
        ProfilerSettings, "get_with_cache", return_value=False
    )
    # Act
    decorator_tester.just_profile_recovery()
    # Assert
    mock_settings.assert_called_once()
    assert not profiler._profiler_events


@pytest.mark.xfail(reason="Test is not done yet")
def test_recovery_measurer(default_group: str, recovery_measurer: RecoveryMeasurer):
    assert recovery_measurer.measure() == pytest.approx(0.1, abs=1e-1)


@pytest.mark.xfail(reason="Test is not done yet")
def test_profile_recovery_time(profiler: "ProfilerWrapper", qtbot: "QtBot"):
    @profile_recovery_time()
    def some_function():
        qtbot.wait(10)

    some_function()
    data = profiler.get_profiler_data("some_function (recovery)")
    assert data == [
        ProfilerResult("some_function", ProfilerSettings.active_group.get(), 0.01)
    ]
