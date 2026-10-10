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

from typing import TYPE_CHECKING

import pytest
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QVBoxLayout, QWidget

from profiler_plugin import env
from profiler_plugin import plugin as plugin_module
from profiler_plugin.plugin import ProfilerPlugin

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


class StubIfaceSignals(QObject):
    initializationCompleted = pyqtSignal()  # noqa: N815


@pytest.fixture(autouse=True)
def _disable_development_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(env.IS_DEVELOPMENT_MODE.key, raising=False)


@pytest.fixture
def iface_signals(mocker: "MockerFixture") -> StubIfaceSignals:
    signals = StubIfaceSignals()
    mock_iface = mocker.patch.object(plugin_module, "iface")
    mock_iface.initializationCompleted = signals.initializationCompleted
    return signals


@pytest.fixture
def profiler_panel() -> QWidget:
    panel = QWidget()
    panel.setLayout(QVBoxLayout())
    return panel


@pytest.fixture
def mock_extension_class(mocker: "MockerFixture") -> "MagicMock":
    return mocker.patch.object(plugin_module, "ProfilerExtension")


def test_extension_is_not_added_before_qgis_initialization_completes(
    mocker: "MockerFixture",
    iface_signals: StubIfaceSignals,
    profiler_panel: QWidget,
    mock_extension_class: "MagicMock",
) -> None:
    # Arrange
    mocker.patch.object(
        plugin_module, "_find_profiler_panel", return_value=profiler_panel
    )
    plugin = ProfilerPlugin()

    # Act
    plugin.initGui()

    # Assert
    mock_extension_class.assert_not_called()
    plugin.unload()


def test_extension_is_added_after_qgis_initialization_completes(
    mocker: "MockerFixture",
    iface_signals: StubIfaceSignals,
    profiler_panel: QWidget,
    mock_extension_class: "MagicMock",
) -> None:
    # Arrange
    mocker.patch.object(
        plugin_module, "_find_profiler_panel", return_value=profiler_panel
    )
    mocker.patch.object(profiler_panel.layout(), "insertWidget")
    mocker.patch.object(profiler_panel.layout(), "removeWidget")
    plugin = ProfilerPlugin()
    plugin.initGui()

    # Act
    iface_signals.initializationCompleted.emit()

    # Assert
    mock_extension_class.assert_called_once()
    plugin.unload()


def test_extension_is_added_immediately_in_development_mode(
    mocker: "MockerFixture",
    monkeypatch: pytest.MonkeyPatch,
    iface_signals: StubIfaceSignals,
    profiler_panel: QWidget,
    mock_extension_class: "MagicMock",
) -> None:
    # Arrange
    # Plugin reloads do not emit initializationCompleted again
    monkeypatch.setenv(env.IS_DEVELOPMENT_MODE.key, "1")
    mocker.patch.object(
        plugin_module, "_find_profiler_panel", return_value=profiler_panel
    )
    mocker.patch.object(profiler_panel.layout(), "insertWidget")
    mocker.patch.object(profiler_panel.layout(), "removeWidget")
    plugin = ProfilerPlugin()

    # Act
    plugin.initGui()

    # Assert
    mock_extension_class.assert_called_once()
    plugin.unload()
