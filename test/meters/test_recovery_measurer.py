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
from qgis_profiler.meters.recovery_measurer import RecoveryMeasurer
from qgis_profiler.settings import ProfilerSettings

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

    from qgis_profiler.profiler import ProfilerWrapper


@pytest.fixture
def recovery_measurer() -> RecoveryMeasurer:
    meter = RecoveryMeasurer.get()
    meter.reset_parameters()
    return meter


def test_recovery_measurer_should_measure_recovery(recovery_measurer: RecoveryMeasurer):
    assert recovery_measurer.measure() == pytest.approx(0.1, abs=1e-1)


def test_recovery_measurer_should_measure_recovery_if_disabled(
    recovery_measurer: RecoveryMeasurer,
):
    recovery_measurer.enabled = False
    assert not recovery_measurer.measure()


@pytest.mark.usefixtures("recovery_measurer")
def test_profile_recovery_time_decorator_should_profile(
    profiler: "ProfilerWrapper",
    decorator_tester: DecoratorTester,
    mock_profiler: "MagicMock",
):
    # Act
    decorator_tester.just_profile_recovery()
    # Assert
    mock_profiler.add_record.assert_called_once_with(
        "just_profile_recovery (recovery)", "Plugins", pytest.approx(0.1, abs=1e-1)
    )


def test_profile_recovery_time_decorator_should_not_profile_if_profiling_is_disabled(
    profiler: "ProfilerWrapper",
    decorator_tester: DecoratorTester,
    mocker: "MockerFixture",
    mock_profiler: "MagicMock",
):
    # Arrange
    mock_settings = mocker.patch.object(
        ProfilerSettings, "get_with_cache", return_value=False
    )
    # Act
    decorator_tester.just_profile_recovery()
    # Assert
    mock_settings.assert_called_once()
    mock_profiler.add_record.assert_not_called()
