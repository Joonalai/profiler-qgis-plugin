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
from functools import partial
from typing import Optional

from qgis.core import QgsApplication
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

from qgis_profiler.profiler import ProfilerResult


class Dialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()

        self.button = QPushButton("Click Me")
        self.button.clicked.connect(partial(wait, 2))

        self.button2 = QPushButton("Click Me too")
        self.button2.clicked.connect(partial(wait, 5))

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


def wait(wait_ms: int) -> None:
    """Wait for a given number of milliseconds."""
    t = time.time()
    while time.time() - t < wait_ms / 1000:
        QgsApplication.processEvents()


def profiler_data_with_group(
    group: str, profile_data: list[ProfilerResult]
) -> list[ProfilerResult]:
    """Set group for all profiler results."""
    return [
        ProfilerResult(
            result.name,
            group,
            result.duration,
            profiler_data_with_group(group, result.children),
        )
        for result in profile_data
    ]
