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
import uuid
from collections import defaultdict
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional

from qgis.core import QgsApplication, QgsRuntimeProfiler
from qgis.PyQt.QtCore import QCoreApplication, QElapsedTimer, QObject

from qgis_profiler.constants import EPSILON
from qgis_profiler.exceptions import EventNotFoundError, ProfilerNotFoundError
from qgis_profiler.settings import (
    ProfilerSettings,
    resolve_group_name,
    resolve_group_name_with_cache,
)

LOGGER = logging.getLogger(__name__)


@dataclass
class ProfilerResult:
    """
    Represents the result of a profiling operation with hierarchical structure.

    This class encapsulates information about a single profiling result, including
    its name, associated group, duration, and any child profiling results. It is
    designed to represent profiles in a nested format, allowing hierarchical
    analysis of performance metrics.

    :param name: Name of the profiling result.
    :param group: Group or category associated with the profiling result.
    :param duration: Duration in seconds for the profiling result.
    :param children: List of child profiling results nested under this result.
    """

    name: str
    group: str
    duration: float
    children: list["ProfilerResult"] = field(default_factory=list)

    def __eq__(self, other: object) -> bool:
        """
        Overridden to allow approximate equality evaluations
        for floating point values.
        """
        if not isinstance(other, ProfilerResult):
            return NotImplemented
        return (
            self.name == other.name
            and self.group == other.group
            and round(abs(self.duration - other.duration), 3) <= EPSILON
            and self.children == other.children
        )

    @staticmethod
    def parse_from_text(text: str, group: str) -> list["ProfilerResult"]:
        """
        Parses a given text into a list of `ProfilerResult` objects by processing
        the hierarchical structure denoted by indentation and the specified group.
        The function expects a specific format where each line contains profiling
        data to be interpreted.

        :param text: The textual data representing the profiling information. Each
                     line in the text is expected to contain data in a specific format.
        :param group: The group under which the profiling results belong. Provides
                      categorization for the parsed results.
        :return: Returns a list of `ProfilerResult` objects constructed from the
                 provided text input, including all nested hierarchical levels.
        """

        def parse_lines(
            lines: list[str], current_group: str, level: int = 1
        ) -> list["ProfilerResult"]:
            results = []
            while lines:
                line = lines[0]
                line_level = line.count("-")
                if line_level == level:
                    # This line is at the current level
                    lines.pop(0)
                    parts = line.split(": ")
                    name = parts[0].strip("- ").strip()
                    duration = float(parts[1].strip())
                    # Recursively parse children
                    children = parse_lines(lines, current_group, level + 1)
                    results.append(
                        ProfilerResult(name, current_group, duration, children)
                    )
                elif line_level < level:
                    # This line belongs to a parent level or is a group name
                    break
            return results

        lines = text.splitlines()
        # The first line is the name of the group
        return parse_lines(lines[1:], group)


class RecoveryMeasurer(QObject):
    """A class for measuring the recovery time of an operation."""

    def __init__(
        self,
        process_event_count: int,
        normal_time_s: int,
        timeout_s: int,
    ) -> None:
        super().__init__()
        self._process_event_count = process_event_count
        self._normal_time_ms = normal_time_s * 1000
        self._timeout_ms = timeout_s * 1000
        self._timer = QElapsedTimer()
        self._recovery_timer = QElapsedTimer()

    def measure_recovery_time(self) -> float:
        """Measure the recovery time of an operation."""
        self._timer.start()
        LOGGER.debug("Normal time: %sms", self._normal_time_ms)
        while (t := self._measure()) > self._normal_time_ms:
            LOGGER.debug("Recovery time: %sms", t)
            if self._timer.elapsed() > self._timeout_ms:
                raise TimeoutError("Recovery time exceeded timeout.")  # noqa: TRY003
            QCoreApplication.processEvents()
        return round(self._timer.elapsed() / 1000, 3)

    def _measure(self) -> int:
        self._recovery_timer.start()
        for _ in range(self._process_event_count):
            QCoreApplication.processEvents()
        return self._recovery_timer.elapsed()  # ms


class ProfilerWrapper:
    """
    A wrapper for the QgsRuntimeProfiler class
    with some additional functionality.

    Do not initialize directly, use ProfilerWrapper.get() instead.
    """

    _instance: Optional["ProfilerWrapper"] = None

    def __init__(self) -> None:
        profiler = QgsApplication.profiler()
        if profiler is None:
            raise ProfilerNotFoundError
        self._profiler: QgsRuntimeProfiler = profiler
        self._profiler_events: dict[str, list[str]] = defaultdict(list)

    @staticmethod
    def get() -> "ProfilerWrapper":
        if ProfilerWrapper._instance is None:
            ProfilerWrapper._instance = ProfilerWrapper()
        return ProfilerWrapper._instance

    @property
    def groups(self) -> set[str]:
        """Set of all groups in the profiler."""
        return self._profiler.groups()

    @contextmanager
    def profile(
        self,
        name: str,
        group: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Profile a block of code."""
        group = resolve_group_name_with_cache(group)
        try:
            yield self.start(name, group)
        finally:
            self.end(group)

    def create_group(self, group_name: str) -> None:
        """Create an empty group in the profiler."""
        with self.profile("Temporary message", group_name):
            QCoreApplication.processEvents()
        self.clear(group_name)

    def profile_recovery_time(self, name: str, group: Optional[str] = None) -> float:
        """Profile a recovery time after an operation."""
        group = (
            group
            if group is not None
            else ProfilerSettings.recovery_group.get_with_cache()
        )
        recovery_measurer = RecoveryMeasurer(
            process_event_count=ProfilerSettings.process_event_count.get(),
            normal_time_s=ProfilerSettings.normal_time.get(),
            timeout_s=ProfilerSettings.timeout.get(),
        )
        recovery_time = recovery_measurer.measure_recovery_time()
        self.add_record(name, group, recovery_time)
        return recovery_time

    def start(self, name: str, group: str) -> str:
        """
        Start a new profiling event.

        :return: Returns a unique identifier for the event.
        """
        event_id = str(uuid.uuid4())
        self._profiler.start(name, group, event_id)
        self._profiler_events[group].append(event_id)
        return event_id

    def end(self, group: str) -> str:
        """
        End the current profiling event for a group.

        :return: Returns a unique identifier for the event.
        """
        self._profiler.end(group)
        return self._profiler_events.get(group, ["invalid"])[-1]

    def add_record(self, name: str, group: str, time: float) -> str:
        """
        Adds a performance profiling record.

        :param name: Name for the profiling event.
        :param group: Group category for the event being profiled.
        :param time: Time duration associated with the profiling event in seconds.
        :return: Returns a unique identifier for the record.
        """
        event_id = str(uuid.uuid4())
        self._profiler.record(name, time, group, event_id)
        self._profiler_events[group].append(event_id)
        return event_id

    def get_event_time(self, event_id: str, group: Optional[str] = None) -> float:
        """Get the duration of a profiling event in seconds."""
        group = resolve_group_name_with_cache(group)
        if event_id not in self._profiler_events[group]:
            raise EventNotFoundError(event_id, group)
        return self._profiler.profileTime(event_id, group)

    def get_profiler_data(
        self, name: Optional[str] = None, group: Optional[str] = None
    ) -> list[ProfilerResult]:
        """
        Retrieve profiler data filtered by name and/or group.

        This function extracts profiling data from a resolved group and parses it
        into structured results. It allows optional filtering by entity name.
        """

        # To get the complete tree, the text version has to be parsed
        # Since python bindings do not exist for all needed methods
        group = resolve_group_name_with_cache(group)
        results = ProfilerResult.parse_from_text(self._profiler.asText(group), group)
        if not name:
            return results

        def find_results_with_name(
            name: str, results: list[ProfilerResult]
        ) -> list[ProfilerResult]:
            results_with_name = []
            for result in results:
                if result.name == name:
                    results_with_name.append(result)
                # Use recursion to search in children
                results_with_name.extend(find_results_with_name(name, result.children))
            return results_with_name

        return find_results_with_name(name, results)

    def clear(self, group: Optional[str] = None) -> None:
        """
        Clear all profiling data for a given group.
        This does not remove the group.
        """
        group = resolve_group_name(group)
        self.end(group)
        self.end(group)
        self.end(group)
        self._profiler.clear(group)
        self._profiler_events.pop(group, None)

    def clear_all(self) -> None:
        """
        Clear all profiling data from all groups.
        This does not remove any group.
        """
        for group in self.groups:
            self.clear(group)
        self._profiler.clear()
