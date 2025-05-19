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
from typing import TYPE_CHECKING, Any, Optional, Union

from qgis.core import QgsApplication
from qgis.gui import QgsFilterLineEdit
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QToolButton,
    QTreeView,
    QWidget,
)
from qgis_plugin_tools.tools.i18n import tr
from qgis_plugin_tools.tools.messages import MsgBar
from qgis_plugin_tools.tools.resources import load_ui_from_file

from profiler_plugin.ui.profiler_proxy_model import ProfilerProxyModel
from profiler_plugin.ui.settings_dialog import SettingsDialog
from qgis_profiler.event_recorder import ProfilerEventRecorder
from qgis_profiler.exceptions import ProfilerNotFoundError
from qgis_profiler.meters.map_rendering import MapRenderingMeter
from qgis_profiler.meters.recovery_measurer import RecoveryMeasurer
from qgis_profiler.meters.thread_health_checker import MainThreadHealthChecker
from qgis_profiler.profiler import ProfilerWrapper
from qgis_profiler.settings import Settings
from qgis_profiler.utils import get_rotated_path

if TYPE_CHECKING:
    from qgis.PyQt.QtGui import QIcon

    from qgis_profiler.meters.meter import Meter

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
    button_cprofiler_record: QToolButton
    button_clear: QToolButton
    button_save: QToolButton
    button_settings: QToolButton
    filter_line_edit: QgsFilterLineEdit
    double_spin_box_threshold: QDoubleSpinBox

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
        self._meters_group = Settings.meters_group.get()

        combo_box = profiler_panel.findChild(QComboBox)
        tree_view = profiler_panel.findChild(QTreeView)
        if combo_box is None:
            raise ProfilerNotFoundError(item=tr("Profiler panel combo box"))
        if tree_view is None:
            raise ProfilerNotFoundError(item=tr("Profiler panel tree view"))
        self.combo_box_group: QComboBox = combo_box
        self.combo_box_group.currentIndexChanged.connect(self._update_ui_state)
        self.tree_view = tree_view

        self._filter_proxy_model = ProfilerProxyModel(
            ProfilerWrapper.get().item_model(), self
        )
        self._filter_proxy_model.set_group(self._current_group())
        self._filter_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)

        self._filter_proxy_model.setRecursiveFilteringEnabled(True)
        self.tree_view.setModel(self._filter_proxy_model)

        self.combo_box_group.currentTextChanged.connect(self._reset_proxy_model_group)

        self.filter_line_edit.setShowClearButton(True)
        self.filter_line_edit.setShowSearchIcon(True)
        self.filter_line_edit.setPlaceholderText(tr("Filter profiles"))
        self.filter_line_edit.valueChanged.connect(
            self._filter_proxy_model.setFilterRegExp
        )

        # Threshold spinbox
        self.double_spin_box_threshold.setValue(Settings.show_events_threshold.get())
        self.double_spin_box_threshold.valueChanged.connect(
            lambda: Settings.show_events_threshold.set(
                self.double_spin_box_threshold.value()
            )
        )

        # Configure meters
        self._reset_meters()

        # Configure buttons
        self._configure_buttons()
        self._update_ui_state()

    def start_recording(self) -> None:
        self._toggle_recording()

    def cleanup(self) -> None:
        if self._event_recorder and self._event_recorder.is_recording():
            self._stop_recording()
        for meter in self._meters:
            meter.cleanup()
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
            self.button_cprofiler_record: (
                self._toggle_cprofile_recording,
                "/mIconPythonFile.svg",
            ),
            self.button_clear: (
                self._clear_current_group,
                "/mActionDeleteSelected.svg",
            ),
            self.button_save: (
                self._save_current_group_profile_data,
                "/mActionFileSave.svg",
            ),
            self.button_settings: (
                self._open_settings,
                "/console/iconSettingsConsole.svg",
            ),
        }

        icon: Union[QIcon, str]
        for button, (action, icon) in button_config.items():
            button.setAutoRaise(True)
            if isinstance(icon, str):
                button.setIcon(QgsApplication.getThemeIcon(icon))
            else:
                button.setIcon(icon)
            button.clicked.connect(action)

    def _current_group(self) -> str:
        qgis_groups = ProfilerWrapper.get().qgis_groups()
        text = self.combo_box_group.currentText()
        return qgis_groups.get(text, text)

    def _reset_proxy_model_group(self, _: str) -> None:
        self._filter_proxy_model.set_group(self._current_group())

    def _reset_meters(self) -> None:
        self.cleanup()
        self._meters_group = Settings.meters_group.get()

        if Settings.recovery_meter_enabled.get():
            self._meters.append(RecoveryMeasurer.get())
        else:
            RecoveryMeasurer.get().enabled = False

        if Settings.thread_health_checker_enabled.get():
            self._meters.append(MainThreadHealthChecker.get())
        else:
            MainThreadHealthChecker.get().enabled = False

        if Settings.map_rendering_meter_enabled.get():
            self._meters.append(MapRenderingMeter.get())
        else:
            MapRenderingMeter.get().enabled = False

        for meter in self._meters:
            meter.reset_parameters()
            meter.connect_to_profiler()

        if self._event_recorder:
            self._event_recorder.event_finished.connect(
                self._event_recorder_event_finished
            )
            self._event_recorder.event_started.connect(
                self._event_recorder_event_started
            )

    def _event_recorder_event_started(self, event_name: str) -> None:
        for meter in self._meters:
            meter.add_context(event_name, self._meters_group)

    def _event_recorder_event_finished(self, _: str) -> None:
        for meter in self._meters:
            meter.measure()
            meter.pop_context()

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

    def _save_current_group_profile_data(self) -> None:
        start_path = Path(Settings.cprofiler_profile_path.get()).parent
        start_path.mkdir(parents=True, exist_ok=True)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Save Profiler Results"),
            str(start_path),
            tr("Profiler Files (*.prof);;All Files (*)"),
        )
        if file_path:
            path = Path(file_path)
            if not path.suffix:
                path = path.with_name(path.name + ".prof")
            ProfilerWrapper.get().save_profiler_results_as_prof_file(
                self._current_group(), path
            )
            MsgBar.info(
                tr("Profiler results saved"),
                tr("File saved to {}", str(file_path)),
                success=True,
            )

    def _toggle_cprofile_recording(self) -> None:
        if not ProfilerWrapper.get().cprofiler_available:
            return

        if not ProfilerWrapper.get().cprofiler.is_profiling():
            ProfilerWrapper.get().cprofiler.enable()
        else:
            ProfilerWrapper.get().cprofiler.disable()
            max_line_count = Settings.cprofiler_log_line_count.get()
            report = ProfilerWrapper.get().cprofiler.get_stat_report(
                "cumtime", max_line_count=max_line_count, trim_zeros=True
            )

            LOGGER.info(
                "CProfiler report (rows with 0.00 times are trimmed):\n%s", report
            )
            output_file_path = Path(Settings.cprofiler_profile_path.get())
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            output_file_path = get_rotated_path(output_file_path)
            ProfilerWrapper.get().cprofiler.dump_stats(output_file_path)
            MsgBar.info(
                tr("Profiler results saved"),
                tr("File saved to {}", str(output_file_path)),
                success=True,
            )

        self._update_ui_state()

    def _start_recording(self) -> None:
        if not self._event_recorder:
            return
        self._event_recorder.start_recording()
        for meter in self._meters:
            if meter.supports_continuous_measuring:
                meter.start_measuring()

    def _stop_recording(self) -> None:
        if not self._event_recorder:
            return
        self._event_recorder.stop_recording()
        for meter in self._meters:
            if meter.supports_continuous_measuring:
                meter.stop_measuring()

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
        self.button_cprofiler_record.setEnabled(
            ProfilerWrapper.get().cprofiler_available
        )

        if not self._event_recorder:
            self.button_record.setToolTip(tr("Cannot use the recording functionality"))

        self.button_record.setChecked(
            self._event_recorder is not None and self._event_recorder.is_recording()
        )
        if ProfilerWrapper.get().cprofiler_available:
            self.button_cprofiler_record.setChecked(
                ProfilerWrapper.get().cprofiler.is_profiling()
            )
        self.button_clear.setEnabled(
            self.combo_box_group.currentText()
            not in ProfilerWrapper.get().qgis_groups()
        )
