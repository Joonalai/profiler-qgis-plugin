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
from collections.abc import Iterator
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from profiler_test_utils.decorator_utils import ClassDecoratorTester, DecoratorTester
from profiler_test_utils.utils import Dialog
from qgis_profiler.meters.recovery_measurer import RecoveryMeasurer
from qgis_profiler.meters.thread_health_checker import MainThreadHealthChecker
from qgis_profiler.profiler import ProfilerWrapper
from qgis_profiler.settings import ProfilerSettings

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from pytestqt.qtbot import QtBot
    from qgis.PyQt.QtWidgets import (
        QWidget,
    )

LOGGER = logging.getLogger(__name__)

WAIT_AFTER_MOUSE_MOVE = 1


@pytest.fixture
def profiler() -> ProfilerWrapper:
    return ProfilerWrapper.get()


@pytest.fixture(autouse=True)
def _clear_profiling_data_and_reset_settings(profiler: "ProfilerWrapper"):
    ProfilerSettings.reset()
    profiler.clear_all()


@pytest.fixture
def default_group() -> str:
    return ProfilerSettings.active_group.get()


@pytest.fixture
def meters_group() -> str:
    return ProfilerSettings.meters_group.get()


@pytest.fixture
def log_profiler_data(profiler: ProfilerWrapper, default_group: str) -> Iterator[None]:
    assert profiler._qgis_profiler
    yield
    LOGGER.info("Profiler data:\n\n%s", profiler._qgis_profiler.asText(default_group))


@pytest.fixture
def mock_settings(mocker: "MockerFixture") -> MagicMock:
    return mocker.patch.object(ProfilerSettings, "get_with_cache")


@pytest.fixture
def mock_profiler(mocker: "MockerFixture") -> MagicMock:
    mock_profiler = mocker.create_autospec(ProfilerWrapper, instance=True)
    mocker.patch.object(ProfilerWrapper, "get", return_value=mock_profiler)
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
def dialog(qtbot: "QtBot", qgis_parent: "QWidget") -> Dialog:
    dialog = Dialog(qgis_parent)
    qtbot.addWidget(dialog)
    dialog.show()

    # Move mouse to the dialog and simulate some mouse movements
    qtbot.mouseMove(dialog)
    qtbot.wait(WAIT_AFTER_MOUSE_MOVE)
    qtbot.wait(WAIT_AFTER_MOUSE_MOVE)
    return dialog


@pytest.fixture
def decorator_tester() -> DecoratorTester:
    return DecoratorTester()


@pytest.fixture
def class_decorator_tester() -> ClassDecoratorTester:
    return ClassDecoratorTester()
