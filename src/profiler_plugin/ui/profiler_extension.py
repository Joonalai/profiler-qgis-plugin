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
from contextlib import suppress
from pathlib import Path
from typing import Any, Optional

from qgis.core import QgsApplication
from qgis.PyQt.QtWidgets import QComboBox, QToolButton, QWidget
from qgis_plugin_tools.tools.i18n import tr
from qgis_plugin_tools.tools.resources import load_ui_from_file

from profiler_plugin.ui.settings_dialog import SettingsDialog
from qgis_profiler.event_recorder import ProfilerEventRecorder
from qgis_profiler.exceptions import ProfilerNotFoundError
from qgis_profiler.meters.meter import Meter, MeterAnomaly
from qgis_profiler.meters.recovery_measurer import RecoveryMeasurer
from qgis_profiler.profiler import ProfilerWrapper
from qgis_profiler.settings import ProfilerSettings

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
        self._event_recorder: Optional[ProfilerEventRecorder] = event_recorder
        self._meters: list[Meter] = []
        self._meters_group = ProfilerSettings.meters_group.get()

        combo_box = profiler_panel.findChild(QComboBox)
        if combo_box is None:
            raise ProfilerNotFoundError(item=tr("Profiler panel combo box"))
        self.combo_box_group: QComboBox = combo_box
        self.combo_box_group.currentIndexChanged.connect(self._update_ui_state)
        self._initial_groups = {
            self.combo_box_group.itemText(i)
            for i in range(self.combo_box_group.count())
        }

        # Configure meters
        self._reset_meters()

        # Configure buttons
        self._configure_buttons()
        self._update_ui_state()

    def cleanup(self) -> None:
        if self._event_recorder and self._event_recorder.is_recording():
            self._stop_recording()
        for meter in self._meters:
            meter.cleanup()
            with suppress(TypeError):
                meter.anomaly_detected.disconnect(self._profile_meter_anomaly)
        self._meters.clear()

        with suppress(TypeError):
            if self._event_recorder:
                self._event_recorder.event_finished.disconnect(
                    self._event_recorder_event_finished
                )

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
            ),  # Not implemented yet
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

    def _reset_meters(self) -> None:
        self.cleanup()
        self._meters_group = ProfilerSettings.meters_group.get()

        if ProfilerSettings.recovery_meter_enabled.get():
            self._meters.append(RecoveryMeasurer.get())
        else:
            RecoveryMeasurer.get().enabled = False

        for meter in self._meters:
            meter.reset_parameters()
            meter.anomaly_detected.connect(self._profile_meter_anomaly)

        if self._event_recorder:
            self._event_recorder.event_finished.connect(
                self._event_recorder_event_finished
            )

    def _profile_meter_anomaly(self, anomaly: MeterAnomaly) -> None:
        LOGGER.debug("Meter anomaly: %s", anomaly)
        ProfilerWrapper.get().add_record(
            anomaly.name, self._meters_group, anomaly.duration_seconds
        )

    def _event_recorder_event_finished(self, event_name: str) -> None:
        RecoveryMeasurer.get().set_context(f"{event_name} (recovery)")
        RecoveryMeasurer.get().measure()

    def _toggle_recording(self) -> None:
        if not self._event_recorder:
            return

        recorder_group = self._event_recorder.group
        available_groups = {
            self.combo_box_group.itemText(i)
            for i in range(self.combo_box_group.count())
        }
        if not self._event_recorder.is_recording():
            if recorder_group not in available_groups:
                ProfilerWrapper.get().create_group(recorder_group)
            self.combo_box_group.setCurrentText(recorder_group)
            self._start_recording()
        else:
            self._stop_recording()

        self._update_ui_state()

    def _start_recording(self) -> None:
        if not self._event_recorder:
            return
        self._event_recorder.start_recording()

    def _stop_recording(self) -> None:
        if not self._event_recorder:
            return
        self._event_recorder.stop_recording()

    def _clear_current_group(self) -> None:
        current_group = self.combo_box_group.currentText()
        ProfilerWrapper.get().clear(current_group)
        self._update_ui_state()

    def _open_settings(self) -> None:
        SettingsDialog().exec()
        # There might be changes in meter configuration
        self._reset_meters()
        self._update_ui_state()

    def _update_ui_state(self, *args: Any) -> None:
        """
        Updates the state of the UI components based on the current profiling state.
        """
        self.button_record.setEnabled(self._event_recorder is not None)
        if not self._event_recorder:
            self.button_record.setToolTip(tr("Cannot use the recording functionality"))

        self.button_record.setChecked(
            self._event_recorder is not None and self._event_recorder.is_recording()
        )
        self.button_clear.setEnabled(
            self.combo_box_group.currentText() not in self._initial_groups
        )
        # TODO: add functionality for saving
        self.button_save.setEnabled(False)
