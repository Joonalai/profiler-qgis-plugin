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
from typing import Any, Optional

from qgis.core import QgsApplication
from qgis.PyQt.QtWidgets import QComboBox, QToolButton, QWidget
from qgis_plugin_tools.tools.i18n import tr
from qgis_plugin_tools.tools.resources import load_ui_from_file

from profiler_plugin.ui.settings_dialog import SettingsDialog
from qgis_profiler.event_recorder import ProfilerEventRecorder
from qgis_profiler.exceptions import ProfilerNotFoundError
from qgis_profiler.profiler import ProfilerWrapper

LOGGER = logging.getLogger(__name__)

UI_CLASS: QWidget = load_ui_from_file(
    str(Path(__file__).parent.joinpath("profiler_extension.ui"))
)


class ProfilerExtension(QWidget, UI_CLASS):
    """
    Represents a Profiler Extension Widget in the GUI.
    Provides functionalities to control profiling operations,
    manage recording, clear profiling data, and access settings.
    """

    button_record: QToolButton
    button_clear: QToolButton
    button_save: QToolButton
    button_settings: QToolButton

    def __init__(
        self, event_recorder: Optional[ProfilerEventRecorder], profiler_panel: QWidget
    ) -> None:
        """
        :param event_recorder: Event recording utility for profiling.
        :param profiler_panel: Main UI panel for the profiler tool.
        """
        super().__init__(profiler_panel)
        self.setupUi(self)
        self._action_recorder: Optional[ProfilerEventRecorder] = event_recorder
        self._settings_dialog = SettingsDialog()
        combo_box = profiler_panel.findChild(QComboBox)
        if combo_box is None:
            raise ProfilerNotFoundError(item=tr("Profiler panel combo box"))
        self.combo_box_group: QComboBox = combo_box
        self.combo_box_group.currentIndexChanged.connect(self._update_ui_state)
        self._initial_groups = {
            self.combo_box_group.itemText(i)
            for i in range(self.combo_box_group.count())
        }

        # Configure buttons
        self._configure_buttons()
        self._update_ui_state()

    def _configure_buttons(self) -> None:
        """
        Configures the buttons with icons, tooltips, and connect them to their actions.
        """
        button_config = {
            self.button_record: (
                self._toggle_recording,
                "/mActionRecord.svg",
            ),
            self.button_clear: (
                self._clear_current_group,
                "/mActionDeleteSelected.svg",
            ),
            self.button_save: (
                None,
                "/mActionFileSave.svg",
            ),  # Disabled by default
            self.button_settings: (
                self._open_settings,
                "/console/iconSettingsConsole.svg",
            ),
        }

        for button, (action, icon) in button_config.items():
            button.setAutoRaise(True)
            button.setIcon(QgsApplication.getThemeIcon(icon))
            if action:
                button.clicked.connect(action)

    def _toggle_recording(self) -> None:
        if not self._action_recorder:
            return

        recorder_group = self._action_recorder.group
        available_groups = {
            self.combo_box_group.itemText(i)
            for i in range(self.combo_box_group.count())
        }
        if not self._action_recorder.is_recording():
            if recorder_group not in available_groups:
                ProfilerWrapper.get().create_group(recorder_group)
            self.combo_box_group.setCurrentText(recorder_group)
            self._action_recorder.start_recording()
        else:
            self._action_recorder.stop_recording()

        self._update_ui_state()

    def _clear_current_group(self) -> None:
        current_group = self.combo_box_group.currentText()
        ProfilerWrapper.get().clear(current_group)
        self._update_ui_state()

    def _open_settings(self) -> None:
        self._settings_dialog.show()
        self._update_ui_state()

    def _update_ui_state(self, *args: Any) -> None:
        """
        Updates the state of the UI components based on the current profiling state.
        """
        self.button_record.setEnabled(self._action_recorder is not None)
        if not self._action_recorder:
            self.button_record.setToolTip(tr("Cannot use the recording functionality"))

        self.button_record.setChecked(
            self._action_recorder is not None and self._action_recorder.is_recording()
        )
        self.button_clear.setEnabled(
            self.combo_box_group.currentText() not in self._initial_groups
        )
        # TODO: add functionality for saving
        self.button_save.setEnabled(False)
