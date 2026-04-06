#  Copyright (c) 2025-2026 profiler-qgis-plugin contributors.
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

"""Proxy model for filtering profiler results by group and elapsed-time threshold."""

import enum
import logging

from qgis.PyQt.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    Qt,
)
from qgis_profiler.settings import Settings

LOGGER = logging.getLogger(__name__)

_user_role = int(Qt.ItemDataRole.UserRole)


class Role(enum.Enum):
    """Define custom data roles for the profiler model."""

    Name = _user_role + 1
    Group = _user_role + 2
    Elapsed = _user_role + 3
    ParentElapsed = _user_role + 4
    Id = _user_role + 5


class ProfilerProxyModel(QSortFilterProxyModel):
    """Rewrite of QGIS C++ QgsProfilerProxyModel.

    Needed to filter the profiles.

    Use QgsFilterProxyModel as a base class when python bindings are available.
    """

    def __init__(
        self, source_model: QAbstractItemModel, parent: QObject | None = None
    ) -> None:
        """Initialize with a source model and optional parent."""
        self.group = ""
        super().__init__(parent)
        self.setSourceModel(source_model)
        self.threshold = Settings.show_events_threshold.get()
        Settings.show_events_threshold.value.changed.connect(self._threshold_changed)

    def set_group(self, group: str) -> None:
        """Set the active group filter and refresh the view."""
        self.group = group
        self.invalidateFilter()

    def set_threshold(self, threshold: float) -> None:
        """Set the minimum elapsed-time threshold and refresh the view."""
        LOGGER.debug("Threshold set to %s", threshold)
        self.threshold = threshold
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # noqa: N802
        """Return whether a row passes the group and threshold filters."""
        result = super().filterAcceptsRow(source_row, source_parent)
        if not result or self.group == "":
            return False

        index = self.sourceModel().index(source_row, 0, source_parent)
        if self.sourceModel().data(index, Role.Group.value) != self.group:
            return False

        return self.sourceModel().data(index, Role.Elapsed.value) >= self.threshold or (
            source_parent.isValid()
            and self.sourceModel().data(index, Role.ParentElapsed.value)
            >= self.threshold
        )

    def _threshold_changed(self) -> None:
        self.set_threshold(Settings.show_events_threshold.get())
