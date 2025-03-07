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
from typing import ClassVar

from qgis.PyQt.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant
from qgis_plugin_tools.tools.i18n import tr

from qgis_profiler.macro import Macro


class MacroTableModel(QAbstractTableModel):
    headers: ClassVar[dict[int, str]] = {0: tr("Macro")}

    def __init__(self) -> None:
        super().__init__()
        self.macros: list[Macro] = []

    def add_macro(self, macro: Macro) -> None:
        row = len(self.macros)
        self.beginInsertRows(QModelIndex(), row, row)

        self.macros.append(macro)

        # Notify the view that rows have been added
        self.endInsertRows()

    def remove_macro(self, row: int) -> None:
        self.beginRemoveRows(QModelIndex(), row, row)
        self.macros.pop(row)
        self.endRemoveRows()

    def rowCount(self, parent: QModelIndex) -> int:  # noqa: N802
        valid = parent.isValid()
        return 0 if valid else len(self.macros)

    def columnCount(self, parent: QModelIndex) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.headers)

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: Qt.ItemDataRole = Qt.DisplayRole,
    ) -> QVariant:
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers.get(section, QVariant())
        if role == Qt.TextAlignmentRole and orientation == Qt.Horizontal:
            return Qt.AlignLeft
        return QVariant()

    def data(
        self, index: QModelIndex, role: Qt.ItemDataRole = Qt.DisplayRole
    ) -> QVariant:
        row = index.row()
        if not index.isValid():
            return QVariant()
        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft
        if role in (Qt.DisplayRole, Qt.ToolTipRole):
            return QVariant(self.macros[row].name)

        return QVariant()
