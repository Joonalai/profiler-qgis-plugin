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
from functools import partial
from typing import TYPE_CHECKING, Optional
from unittest.mock import MagicMock

import pytest
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QLineEdit,
    QListWidget,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from qgis_profiler.profiler import ProfilerWrapper
from qgis_profiler.settings import ProfilerSettings
from test import utils

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from pytestqt.qtbot import QtBot

LOGGER = logging.getLogger(__name__)

WAIT_AFTER_MOUSE_MOVE = 1


class Dialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()

        self.button = QPushButton("Click Me")
        self.button.clicked.connect(partial(utils.wait, 2))

        self.button2 = QPushButton("Click Me too")
        self.button2.clicked.connect(partial(utils.wait, 5))

        self.combobox = QComboBox()
        self.combobox.addItems(["Item 1", "Item 2", "Item 3"])
        self.line_edit = QLineEdit()
        self.radio_button = QRadioButton("Option 1")
        self.check_box = QCheckBox("Check Me")
        self.list_widget = QListWidget()
        self.list_widget.addItems(["List Item 1", "List Item 2", "List Item 3"])

        layout.addWidget(self.button)
        layout.addWidget(self.button2)
        layout.addWidget(self.combobox)
        layout.addWidget(self.line_edit)
        layout.addWidget(self.radio_button)
        layout.addWidget(self.check_box)
        layout.addWidget(self.list_widget)

        self.setLayout(layout)


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
def log_profiler_data(profiler: ProfilerWrapper, default_group: str) -> Iterator[None]:
    assert profiler._profiler
    yield
    LOGGER.info("Profiler data:\n\n%s", profiler._profiler.asText(default_group))


@pytest.fixture
def mock_settings(mocker: "MockerFixture") -> MagicMock:
    return mocker.patch.object(ProfilerSettings, "get_with_cache")


@pytest.fixture
def mock_profiler(mocker: "MockerFixture") -> MagicMock:
    mock_profiler = mocker.create_autospec(ProfilerWrapper, instance=True)
    mocker.patch.object(ProfilerWrapper, "get", return_value=mock_profiler)
    return mock_profiler


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
def dialog_widget_positions(dialog: Dialog) -> dict[str, utils.WidgetInfo]:
    return {
        name: utils.WidgetInfo.from_widget(name, widget)
        for name in dir(dialog)
        if isinstance((widget := getattr(dialog, name, None)), QWidget)
    }
