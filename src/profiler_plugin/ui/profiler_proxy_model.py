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
import enum
import logging
from typing import Optional

from qgis.PyQt.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    Qt,
)

LOGGER = logging.getLogger(__name__)

_user_role = int(Qt.UserRole)


class Role(enum.Enum):
    Name = _user_role + 1
    Group = _user_role + 2
    Elapsed = _user_role + 3
    ParentElapsed = _user_role + 4
    Id = _user_role + 5


class ProfilerProxyModel(QSortFilterProxyModel):
    """
    Rewrite of QGIS C++ QgsProfilerProxyModel.
    Needed to filter the profiles.

    Use QgsFilterProxyModel as a base class when python bindings are available.
    """

    def __init__(
        self, source_model: QAbstractItemModel, parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)
        self.group = ""
        self.setSourceModel(source_model)

    def set_group(self, group: str) -> None:
        self.group = group
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # noqa: N802
        result = super().filterAcceptsRow(source_row, source_parent)
        if not result or self.group == "":
            return False

        index = self.sourceModel().index(source_row, 0, source_parent)
        return self.sourceModel().data(index, Role.Group.value) == self.group
