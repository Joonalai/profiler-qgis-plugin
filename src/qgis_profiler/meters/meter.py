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
import abc
from typing import NamedTuple

from qgis.PyQt.QtCore import QObject, pyqtSignal, pyqtSlot


class MeterAnomaly(NamedTuple):
    name: str
    duration_seconds: float


class Meter(QObject):
    __metaclass__ = abc.ABCMeta

    anomaly_detected = pyqtSignal(MeterAnomaly)

    def __init__(self) -> None:
        super().__init__(None)
        self._context: str = self.__class__.__name__

    @property
    def current_context(self) -> str:
        return self._context

    @pyqtSlot()
    @abc.abstractmethod
    def measure(self) -> float:
        """
        Measure once with the meter. Signal anomaly_detected will be emitted
        if applicable.

        :return: duration in seconds.
        """

    def _emit_anomaly(self, duration: float) -> None:
        self.anomaly_detected.emit(MeterAnomaly(self.current_context, duration))
