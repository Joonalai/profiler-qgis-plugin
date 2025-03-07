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
from pathlib import Path
from typing import Any, Optional

from qgis.core import QgsApplication
from qgis.gui import QgsDevToolWidget, QgsDevToolWidgetFactory
from qgis.PyQt.QtWidgets import (
    QHeaderView,
    QInputDialog,
    QTableView,
    QToolButton,
    QWidget,
)
from qgis_plugin_tools.tools.i18n import tr
from qgis_plugin_tools.tools.resources import load_ui_from_file

from profiler_plugin.ui.macro.macro_model import MacroTableModel
from qgis_profiler.macro import MacroPlayer, MacroRecorder
from qgis_profiler.profiler import profiler
from qgis_profiler.settings import ProfilerSettings

UI_CLASS: QWidget = load_ui_from_file(
    str(Path(__file__).parent.joinpath("macro_panel.ui"))
)


class MacroPanel(UI_CLASS, QgsDevToolWidget):
    button_record: QToolButton
    button_play: QToolButton
    button_delete: QToolButton
    table_view: QTableView

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self._recorder = MacroRecorder(
            widgets_to_filter_events_out=[self, self.button_record]
        )
        self._player = MacroPlayer(playback_speed=0.7)
        self._model = MacroTableModel()

        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.setModel(self._model)

        self.button_record.setAutoRaise(True)
        self.button_record.setIcon(QgsApplication.getThemeIcon("/mActionRecord.svg"))

        self.button_play.setAutoRaise(True)
        self.button_play.setIcon(QgsApplication.getThemeIcon("/mActionPlay.svg"))

        self.button_delete.setAutoRaise(True)
        self.button_delete.setIcon(
            QgsApplication.getThemeIcon("/mActionDeleteSelected.svg")
        )

        self.button_record.clicked.connect(self._toggle_recording)
        self.button_play.clicked.connect(self._play_macro)
        self.button_delete.clicked.connect(self._delete_macros)
        self.table_view.selectionModel().selectionChanged.connect(self._update)
        self._update()

    def _toggle_recording(self) -> None:
        if not self._recorder.recording:
            self._recorder.start()
        else:
            macro = self._recorder.stop()

            name, ok = QInputDialog.getText(
                self, tr("Macro Name"), tr("Enter the name of the macro:")
            )
            if ok:
                macro.name = name
                # TODO: save macro as serialized to settings as well
                self._model.add_macro(macro)
        self._update()

    def _play_macro(self) -> None:
        if not self._model.macros or not (indexes := self.table_view.selectedIndexes()):
            return
        macro = self._model.macros[indexes[0].row()]

        if ProfilerSettings.profiler_enabled.get():
            # Profile playing of the macro
            group_name = ProfilerSettings.active_group.get()
            with profiler.profile(f"Macro: {macro.name}", group_name):
                self._player.play(macro)
            # TODO: make setting of recovery
            profiler.profile_recovery_time(f"Macro: {macro.name} (recovery)")
        else:
            self._player.play(macro)

    def _delete_macros(self) -> None:
        if not self._model.macros or not (indexes := self.table_view.selectedIndexes()):
            return
        for index in reversed(indexes):
            self._model.remove_macro(index.row())
        self._update()

    def _update(self, *args: Any) -> None:
        self.button_record.setChecked(self._recorder.recording)
        self.button_play.setEnabled(len(self.table_view.selectedIndexes()) == 1)
        self.button_delete.setEnabled(bool(self.table_view.selectedIndexes()))


class MacroToolFactory(QgsDevToolWidgetFactory):
    def __init__(self) -> None:
        super().__init__(
            tr("Macro dev tool"),
            QgsApplication.getThemeIcon("/mActionRecord.svg"),
        )

    def createWidget(self, parent: Optional[QWidget] = None) -> MacroPanel:  # noqa: N802
        return MacroPanel()
