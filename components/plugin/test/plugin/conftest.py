#  Copyright (c) 2025-2026 profiler-qgis-plugin contributors.
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
from os.path import normpath
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from qgis_plugin_tools.tools import resources
from qgis_profiler.meters.map_rendering import MapRenderingMeter
from qgis_profiler.meters.recovery_measurer import RecoveryMeasurer
from qgis_profiler.meters.thread_health_checker import MainThreadHealthChecker
from qgis_profiler.profiler import ProfilerWrapper
from qgis_profiler.settings import Settings

import profiler_plugin

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pytest_mock import MockerFixture

LOGGER = logging.getLogger(__name__)

WAIT_AFTER_MOUSE_MOVE = 1

PLUGIN_DIR = Path(profiler_plugin.__file__).parent


@pytest.fixture(scope="session", autouse=True)
def _resolve_plugin_path_to_profiler_plugin() -> "Iterator[None]":
    """Resolve qgis_plugin_tools plugin path to profiler_plugin in all calls.

    qgis_plugin_tools finds the plugin by walking the call stack for a plugin
    package. Test modules and qgis_profiler are not inside profiler_plugin, so
    calls made from them (e.g. Settings.reset()) would resolve to a fallback
    plugin name and read/write a different QSettings section than the plugin
    code under test.
    """
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            resources,
            "plugin_path",
            lambda *args: normpath(PLUGIN_DIR.joinpath(*args)),
        )
        assert resources.plugin_name() == "Profiler"
        yield


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


@pytest.fixture
def mock_map_rendering_meter(mocker: "MockerFixture") -> MagicMock:
    mock_meter = mocker.MagicMock()
    mocker.patch.object(MapRenderingMeter, "get", return_value=mock_meter)
    return mock_meter
