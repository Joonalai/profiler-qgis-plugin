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
from collections.abc import Generator
from contextlib import contextmanager, suppress
from typing import Any, Callable, ClassVar, NamedTuple, Optional

from qgis.PyQt.QtCore import QObject, pyqtSignal, pyqtSlot

from qgis_profiler import decorators
from qgis_profiler.profiler import ProfilerWrapper
from qgis_profiler.settings import ProfilerSettings, resolve_group_name_with_cache


class MeterContext(NamedTuple):
    """Context of a meter."""

    name: str
    group: str

    def with_meter_suffix(self, suffix: str) -> "MeterContext":
        return MeterContext(f"{self.name} ({suffix})", self.group)


class MeterAnomaly(NamedTuple):
    """Anomaly detected by a meter."""

    context: MeterContext
    duration_seconds: float


class Meter(QObject):
    __metaclass__ = abc.ABCMeta

    _short_name: ClassVar[str] = ""

    anomaly_detected = pyqtSignal(MeterAnomaly)

    def __init__(self) -> None:
        super().__init__(None)
        self._default_context = MeterContext(
            self.__class__.__name__, ProfilerSettings.meters_group.get()
        )
        self._context_stack: list[MeterContext] = []
        self._enabled = True
        self._connected_to_profiler = False

    @classmethod
    @abc.abstractmethod
    def get(cls: type["Meter"]) -> "Meter":
        """
        Get a singleton instance of the meter.
        """

    @classmethod
    def monitor(
        cls,
        name: Optional[str] = None,
        group: Optional[str] = None,
        name_args: Optional[list[str]] = None,
        connect_to_profiler: bool = True,  # noqa: FBT001, FBT002
        measure_after_call: bool = False,  # noqa: FBT001, FBT002
    ) -> Callable:
        """
        Decorator for monitoring the meter by setting the meter context
        within a function call and by optionally measuring the meter
        after the function call. If the meter is disabled, nothing is done.

        If you want to profile the anomalies found during the function call,
        connect to profiler using the `connect_to_profiler` argument.

        :param name: Optional name for this context. If not provided, the
        name of the function being wrapped will be used.
        :param group: Optional group name for the context. If not provided,
        the group name is read from settings.
        :param name_args: Optional list of argument names to include in the context
        name. If specified, the context name will include these argument values.
        :param connect_to_profiler: Optional flag to connect to meter to a profiler
        if not yet connected.
        :param measure_after_call: Optional flag to measure the meter after the function
        call.
        :return: A callable decorator function that wraps the given function to
        set the meter context during the function call.
        """

        def context_wrapper(function: Callable) -> Callable:
            from functools import wraps

            @wraps(function)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                group_name = resolve_group_name_with_cache(group)
                context_name = name if name is not None else function.__name__
                if name_args:
                    context_name += decorators._parse_arguments(
                        function, name_args, args, kwargs
                    )

                meter = cls.get()
                if not meter.enabled:
                    return function(*args, **kwargs)

                if connect_to_profiler and not meter.is_connected_to_profiler:
                    meter.connect_to_profiler()
                with meter.context(context_name, group_name):
                    try:
                        return function(*args, **kwargs)
                    finally:
                        if measure_after_call:
                            meter.measure()

            return wrapper

        return context_wrapper

    @property
    def current_context(self) -> MeterContext:
        """
        :return The current context of the meter.
        """
        context = (
            self._context_stack[-1] if self._context_stack else self._default_context
        )

        if self._short_name:
            return context.with_meter_suffix(self._short_name)
        return context

    @property
    def is_connected_to_profiler(self) -> bool:
        """:return Whether the meter is connected to the profiler."""
        return self._connected_to_profiler

    @property
    def enabled(self) -> bool:
        """:return Whether the meter is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    @contextmanager
    def context(self, name: str, group: str) -> Generator[MeterContext, None, None]:
        """Context manager for the meter in certain context."""
        self.add_context(name, group)
        try:
            yield self.current_context
        finally:
            self.pop_context()

    def add_context(self, name: str, group: str) -> None:
        """
        Adds context to the context stack
        """
        self._context_stack.append(MeterContext(name, group))

    def pop_context(self) -> Optional[MeterContext]:
        """
        Remove the last context from the context stack if it exists.

        :return: Context or None if context stack is empty.
        """
        if self._context_stack:
            return self._context_stack.pop()
        return None

    def connect_to_profiler(self) -> None:
        """
        Connects anomaly detection signal to profiler's anomaly handling.

        This method establishes a connection between the
        `anomaly_detected` signal and the `_profile_anomaly`
        handler to ensure anomalies are routed correctly.

        :return: None
        """
        self.anomaly_detected.connect(self._profile_anomaly)
        self._connected_to_profiler = True

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
        with suppress(TypeError):
            self.anomaly_detected.disconnect(self._profile_anomaly)
        self._connected_to_profiler = False

    @staticmethod
    @pyqtSlot(MeterAnomaly)
    def _profile_anomaly(anomaly: MeterAnomaly) -> None:
        """Profile the anomaly."""
        ProfilerWrapper.get().add_record(
            anomaly.context.name, anomaly.context.group, anomaly.duration_seconds
        )

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
        """Emit anomaly_detected signal."""
        self.anomaly_detected.emit(MeterAnomaly(self.current_context, duration))
