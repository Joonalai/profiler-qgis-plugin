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
import cProfile
import io
import pstats
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from types import CodeType
from typing import TYPE_CHECKING, Any, Union

from qgis_profiler.constants import EPSILON

if TYPE_CHECKING:
    from _lsprof import profiler_entry  # noqa: SC200


@dataclass
class ProfilerEntry:
    """
    Class representing a single profiling entry.

    Inspired by _lsprof.profiler_entry and _lsprof.profiler_subentry
    but made more flexible and easier to work with.
    """

    code: str  # code object or built-in function name
    callcount: int = 1  # how many times this was called
    inlinetime: float = 0.0  # inline time in this entry (not in subcalls)
    reccallcount: int = 0  # how many times called recursively
    totaltime: float = 0.0  # total time in this entry
    calls: list["ProfilerEntry"] = field(default_factory=list)  # details of the calls

    @staticmethod
    def from_cprofiler(cprofiler: "cProfile.Profile") -> list["ProfilerEntry"]:
        """Turns a cProfile.Profile stats into a list of ProfilerEntry objects."""
        return [ProfilerEntry.from_stat(stat) for stat in cprofiler.getstats()]

    @staticmethod
    def from_stat(stat: "profiler_entry") -> "ProfilerEntry":
        calls = (
            []
            if not hasattr(stat, "calls") or not stat.calls
            else list(map(ProfilerEntry.from_stat, stat.calls))  # type: ignore
        )
        return ProfilerEntry(
            stat.code.co_name if isinstance(stat.code, CodeType) else stat.code,
            stat.callcount,
            round(stat.inlinetime, 3),
            round(stat.reccallcount, 3),
            round(stat.totaltime, 3),
            calls,
        )

    def __add__(self, other: "ProfilerEntry") -> "ProfilerEntry":
        if self.code != other.code:
            raise ValueError("Cannot add entries with different codes")  # noqa: TRY003
        return ProfilerEntry(
            self.code,
            self.callcount + other.callcount,
            self.inlinetime + other.inlinetime,
            self.reccallcount,
            self.totaltime + other.totaltime,
            self.calls,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProfilerEntry):
            return NotImplemented
        return (
            self.code == other.code
            and self.callcount == other.callcount
            and round(abs(self.inlinetime - other.inlinetime), 3) <= EPSILON
            and self.reccallcount == other.reccallcount
            and round(abs(self.totaltime - other.totaltime), 3) <= EPSILON
            and self.calls == other.calls
        )

    def _extend_calls(self, calls: list["ProfilerEntry"]) -> None:
        call_dict = {call.code: call for call in self.calls}
        for call in calls:
            if call.code in call_dict:
                call_dict[call.code] += call  # type: ignore
            else:
                call_dict[call.code] = call
        self.calls = list(call_dict.values())

    @staticmethod
    def parse_from_qgis_profiler_text(text: str) -> list["ProfilerEntry"]:  # noqa: C901
        """
        Parses a given profiler text into a list of `ProfilerEntry` objects.
        Processes hierarchical structure based on indentation and generates profiling
        entries.
        """

        profile_entries: dict[str, ProfilerEntry] = {}

        def profiler_lines_into_entries(
            lines: list[str],
            parents: set[str],
            level: int = 1,
        ) -> list["ProfilerEntry"]:
            """Insert profiling data into the profile_entries dict."""
            results = []
            while lines:
                line = lines[0]
                line_level = line.count("-")
                if line_level == level:
                    # This line is at the current level
                    lines.pop(0)
                    parts = line.split(": ")
                    name = parts[0].strip("- ").strip()
                    total_time = round(float(parts[1].strip()), 3)
                    entry = ProfilerEntry(name, totaltime=total_time)

                    new_entry = name not in profile_entries
                    if new_entry:
                        profile_entries[name] = entry

                    if name in parents:
                        profile_entries[name].reccallcount += 1

                    # Recursively parse children
                    calls = profiler_lines_into_entries(
                        lines, parents | {name}, level + 1
                    )
                    if calls:
                        profile_entries[name]._extend_calls(calls)
                    else:
                        # No children, inline time should be total time
                        entry.inlinetime = total_time

                    if not new_entry:
                        profile_entries[name] += entry

                    if level > 1:
                        if entry.calls:
                            entry = deepcopy(entry)
                            entry.calls = []
                        results.append(entry)

                elif line_level < level:
                    # This line belongs to a parent level or is a group name
                    break
            return results

        # The first line is the name of the group
        profiler_lines_into_entries(
            text.splitlines()[1:],
            set(),
        )
        return list(profile_entries.values())


class QCProfiler(cProfile.Profile):
    """
    cProfile.Profile subclass with QGIS-specific
    functionality and extra utilities.
    """

    def __init__(self) -> None:
        super().__init__()
        self._qgis_stats: list[ProfilerEntry] = []
        self._profiling: bool = False

    @contextmanager
    def qgis_profiler_data(self, profiler_text: str) -> Generator[None, Any, None]:
        self._qgis_stats = ProfilerEntry.parse_from_qgis_profiler_text(profiler_text)
        try:
            yield
        finally:
            self._qgis_stats = []

    def enable(self, subcalls: bool = True, builtins: bool = True) -> None:  # noqa: FBT001 FBT002
        super().enable(subcalls, builtins)
        self._profiling = True

    def disable(self) -> None:
        super().disable()
        self._profiling = False

    def getstats(self) -> Sequence[Union[ProfilerEntry, "profiler_entry"]]:  # type: ignore[override]
        if self._qgis_stats:
            return self._qgis_stats
        return super().getstats()

    def is_profiling(self) -> bool:
        return self._profiling

    def get_stat_report(
        self,
        sort: Union[str, tuple[str, ...], int] = -1,
        max_line_count: int = 1000,
        trim_zeros: bool = False,  # noqa: FBT001 FBT002
    ) -> str:
        """
        Get the profile report as a string.

        :param sort: Sort method. Can be a string or a tuple of strings.
        :param max_line_count: Maximum number of lines to return.
        :param trim_zeros: Trim lines with zero times from the report.
        :return: The profile report as a string.
        """
        if not isinstance(sort, tuple):
            sort = (sort,)  # type: ignore[assignment]
        with io.StringIO() as stream:
            pstats.Stats(self, stream=stream).strip_dirs().sort_stats(  # type: ignore[misc]
                *sort
            ).print_stats()
            report = stream.getvalue()
        report_lines = []
        if trim_zeros:
            for line in report.splitlines():
                if "0.000    0.000    0.000    0.000" in line:
                    continue
                report_lines.append(line)
        else:
            report_lines = report.splitlines()

        # First 5 lines are part of the header
        return "\n".join(report_lines[: max_line_count + 5])
