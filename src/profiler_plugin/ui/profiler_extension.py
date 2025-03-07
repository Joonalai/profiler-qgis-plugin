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
from pathlib import Path
from typing import Any

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QComboBox, QToolButton, QWidget
from qgis_plugin_tools.tools.resources import load_ui_from_file

from profiler_plugin.ui.settings_dialog import SettingsDialog
from qgis_profiler.action_profiler import ActionProfiler
from qgis_profiler.profiler import profiler

LOGGER = logging.getLogger(__name__)

UI_CLASS: QWidget = load_ui_from_file(
    str(Path(__file__).parent.joinpath("profiler_extension.ui"))
)


class ProfilerExtension(QWidget, UI_CLASS):
    button_record: QToolButton
    button_clear: QToolButton
    button_save: QToolButton
    button_settings: QToolButton

    def __init__(self, action_profiler: ActionProfiler, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self._action_profiler = action_profiler
        self._settings_dialog = SettingsDialog()

        self.combo_box_group: QComboBox = parent.findChild(QComboBox)
        self.combo_box_group.currentIndexChanged.connect(self._update)
        self._initial_groups = {
            self.combo_box_group.itemText(i)
            for i in range(self.combo_box_group.count())
        }

        # Set this here to be able to find the button more easily in ui file
        self.button_record.setAutoRaise(True)
        self.button_clear.setAutoRaise(True)
        self.button_save.setAutoRaise(True)
        self.button_settings.setAutoRaise(True)

        self.button_record.setIcon(QgsApplication.getThemeIcon("/mActionRecord.svg"))
        self.button_clear.setIcon(
            QgsApplication.getThemeIcon("/mActionDeleteSelected.svg")
        )
        self.button_save.setIcon(QgsApplication.getThemeIcon("/mActionFileSave.svg"))
        self.button_settings.setIcon(
            QgsApplication.getThemeIcon("/console/iconSettingsConsole.svg")
        )

        self.button_record.clicked.connect(self._toggle_recording)
        self.button_clear.clicked.connect(self._clear_current_group)
        self.button_settings.clicked.connect(self._open_settings)

        self._update()

    def _toggle_recording(self) -> None:
        if not self._action_profiler.is_recording:
            if self._action_profiler.group not in {
                self.combo_box_group.itemText(i)
                for i in range(self.combo_box_group.count())
            }:
                # Create a group
                with profiler.profile("Start recording", self._action_profiler.group):
                    QCoreApplication.processEvents()
                profiler.clear(self._action_profiler.group)

            self.combo_box_group.setCurrentText(self._action_profiler.group)
            self._action_profiler.start_recording()
        else:
            self._action_profiler.stop_recording()
        self._update()

    def _clear_current_group(self) -> None:
        current_group = self.combo_box_group.currentText()
        profiler.clear(current_group)
        self._update()

    def _open_settings(self) -> None:
        self._settings_dialog.show()
        self._update()

    def _update(self, *args: Any) -> None:
        self.button_record.setChecked(self._action_profiler.is_recording)
        self.button_clear.setEnabled(
            self.combo_box_group.currentText() not in self._initial_groups
        )
        # TODO: add functionality
        self.button_save.setEnabled(False)
