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
from typing import Any, Optional

from qgis.PyQt.QtCore import QT_VERSION_STR, pyqtSignal
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtWidgets import QApplication, QWidget

from qgis_profiler.constants import QT_VERSION_MIN

LOGGER = logging.getLogger(__name__)


def get_widget_under_cursor() -> Optional[QWidget]:
    """Get the widget under mouse cursor"""
    return QApplication.widgetAt(QCursor.pos())


def has_suitable_qt_version(suitable_qt_version: str = QT_VERSION_MIN) -> bool:
    """
    Check if the QT version is recent enough.
    """
    return QT_VERSION_STR >= suitable_qt_version  # noqa: SIM300


def disconnect_signal(signal: pyqtSignal, connection: Any, name: str) -> None:
    """Disconnect connection from signal safely."""
    try:
        signal.disconnect(connection)
    except TypeError:
        LOGGER.exception("Could not disconnect signal %s", name)
