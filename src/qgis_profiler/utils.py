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
from typing import Any, Callable, Optional

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


def parse_arguments(
    function: Callable, event_args: list[str], args: Any, kwargs: Any
) -> str:
    """
    Parses and formats arguments for a given function based on event_args.

    :param function: Function whose arguments are being processed.
    :param event_args: List of argument names to include in the output.
    :param args: Positional arguments passed to the function.
    :param kwargs: Keyword arguments passed to the function.
    :return: Formatted string of key-value pairs for the specified arguments.
    """

    arg_names = function.__code__.co_varnames[: function.__code__.co_argcount]
    arg_dict = {**dict(zip(arg_names, args)), **kwargs}
    arg_values = [
        f"{event_arg}={arg_dict[event_arg]}"
        for event_arg in event_args
        if event_arg in arg_dict
    ]
    return f"({', '.join(arg_values)})"
