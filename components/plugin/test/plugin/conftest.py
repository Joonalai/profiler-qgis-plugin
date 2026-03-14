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
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from qgis_profiler.meters.recovery_measurer import RecoveryMeasurer
from qgis_profiler.meters.thread_health_checker import MainThreadHealthChecker
from qgis_profiler.profiler import ProfilerWrapper
from qgis_profiler.settings import Settings

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

LOGGER = logging.getLogger(__name__)

WAIT_AFTER_MOUSE_MOVE = 1


@pytest.fixture
def profiler() -> ProfilerWrapper:
    return ProfilerWrapper.get()


@pytest.fixture(autouse=True)
def _clear_profiling_data_and_reset_settings(profiler: "ProfilerWrapper") -> None:
    Settings.reset()
    profiler.clear_all()


@pytest.fixture
def mock_settings(mocker: "MockerFixture") -> MagicMock:
    return mocker.patch.object(Settings, "get_with_cache")


@pytest.fixture
def mock_profiler(mocker: "MockerFixture") -> MagicMock:
    mock_profiler = mocker.create_autospec(ProfilerWrapper, instance=True)
    mocker.patch.object(ProfilerWrapper, "get", return_value=mock_profiler)
    mock_profiler.cprofiler.is_profiling = lambda: (
        mock_profiler.cprofiler.enable.call_count
        > mock_profiler.cprofiler.disable.call_count
    )

    return mock_profiler


@pytest.fixture
def mock_meter_recovery_measurer(mocker: "MockerFixture") -> MagicMock:
    mock_meter = mocker.MagicMock()
    mocker.patch.object(RecoveryMeasurer, "get", return_value=mock_meter)
    return mock_meter


@pytest.fixture
def mock_thread_health_checker_meter(mocker: "MockerFixture") -> MagicMock:
    mock_meter = mocker.MagicMock()
    mocker.patch.object(MainThreadHealthChecker, "get", return_value=mock_meter)
    return mock_meter
