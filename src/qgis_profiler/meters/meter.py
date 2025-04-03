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
from typing import NamedTuple, Optional

from qgis.PyQt.QtCore import QObject, pyqtSignal


class MeterAnomaly(NamedTuple):
    name: str
    duration_seconds: float


class Meter(QObject):
    __metaclass__ = abc.ABCMeta

    anomaly_detected = pyqtSignal(MeterAnomaly)

    def __init__(self) -> None:
        super().__init__(None)
        self._context: str = self.__class__.__name__
        self._enabled: bool = True

    @classmethod
    @abc.abstractmethod
    def get(cls: type["Meter"]) -> "Meter":
        """
        Get a singleton instance of the meter.
        """

    @property
    def current_context(self) -> str:
        return self._context

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def set_context(self, context: str) -> None:
        """
        Set the current context of the meter.
        """
        self._context = context

    def measure(self) -> Optional[float]:
        """
        Measure once with the meter. Signal anomaly_detected will be emitted
        if applicable.

        :return: duration in seconds or None if meter is disabled.
        """
        if self.enabled:
            duration, anomaly_detected = self._measure()
            if anomaly_detected:
                self._emit_anomaly(duration)
            return duration
        return None

    def cleanup(self) -> None:
        """
        Cleanup the meter.
        """

    @abc.abstractmethod
    def reset_parameters(self) -> None:
        """
        Reset the meter parameters based on setting values.
        """

    @abc.abstractmethod
    def _measure(self) -> tuple[float, bool]:
        """
        Perform actual measurement.

        :return: A tuple containing a duration in seconds and a
        boolean indicating whether an anomaly was detected.
        """

    def _emit_anomaly(self, duration: float) -> None:
        self.anomaly_detected.emit(MeterAnomaly(self.current_context, duration))
