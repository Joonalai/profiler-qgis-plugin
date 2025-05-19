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

from typing import TYPE_CHECKING, Optional, cast

import qgis_plugin_tools
from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtWidgets import QDockWidget, QVBoxLayout, QWidget
from qgis.utils import iface as iface_
from qgis_plugin_tools.tools.custom_logging import (
    setup_loggers,
)
from qgis_plugin_tools.tools.i18n import tr
from qgis_plugin_tools.tools.messages import MsgBar

import profiler_plugin
import qgis_profiler
from profiler_plugin.ui.profiler_extension import ProfilerExtension
from qgis_profiler import utils
from qgis_profiler.constants import QT_VERSION_MIN
from qgis_profiler.event_recorder import ProfilerEventRecorder
from qgis_profiler.settings import Settings

if TYPE_CHECKING:
    from qgis.gui import QgisInterface

iface = cast("QgisInterface", iface_)


class ProfilerPlugin(QObject):
    name = tr("Profiler")

    def __init__(self) -> None:
        super().__init__(parent=None)
        self._teardown_loggers = lambda: None
        self._profiler_panel_layout: Optional[QVBoxLayout] = None
        self._event_recorder: Optional[ProfilerEventRecorder] = None
        self._profiler_extension: Optional[ProfilerExtension] = None

    def initGui(self) -> None:  # noqa: N802
        self._teardown_loggers = setup_loggers(
            qgis_profiler.__name__,
            profiler_plugin.__name__,
            qgis_plugin_tools.__name__,
            message_log_name=self.name,
        )

        if utils.has_suitable_qt_version(QT_VERSION_MIN):
            self._event_recorder = ProfilerEventRecorder(
                group_name=Settings.recorded_group.get(),
            )
        else:
            MsgBar.error(
                tr("Qt version is too old"),
                tr(
                    "Cannot use feature action profiler. Please upgrade to {}+",
                    QT_VERSION_MIN,
                ),
            )

        self._add_profiler_extension()

    def _add_profiler_extension(self) -> None:
        """
        Modify the QgsProfilerPanelBase to include the ProfilerExtension
        """
        if (tools := iface.mainWindow().findChild(QDockWidget, "DevTools")) is None:
            return
        if (profiler_panel := tools.findChild(QWidget, "QgsProfilerPanelBase")) is None:
            return
        self._profiler_panel_layout = profiler_panel.layout()

        self._profiler_extension = ProfilerExtension(
            self._event_recorder, profiler_panel
        )
        self._profiler_panel_layout.insertWidget(0, self._profiler_extension)
        if Settings.start_recording_on_startup.get():
            self._profiler_extension.start_recording()

    def unload(self) -> None:
        self._teardown_loggers()
        self._teardown_loggers = lambda: None

        if self._profiler_panel_layout:
            self._profiler_panel_layout.removeWidget(self._profiler_extension)
        if self._profiler_extension:
            self._profiler_extension.cleanup()
            self._profiler_extension.deleteLater()
        self._profiler_extension = None  # type:ignore[assignment]
