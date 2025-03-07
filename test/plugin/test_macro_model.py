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
from typing import TYPE_CHECKING

from qgis.PyQt.QtCore import QModelIndex, Qt, QVariant

from profiler_plugin.ui.macro.macro_model import MacroTableModel
from qgis_profiler.macro import Macro

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_macro_table_model_initialization() -> None:
    model = MacroTableModel()

    assert model.rowCount(QModelIndex()) == 0
    assert model.columnCount(QModelIndex()) == 1
    assert model.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "Macro"


def test_macro_table_model_add_macro(mocker: "MockerFixture") -> None:
    model = MacroTableModel()
    macro_mock = mocker.Mock(spec=Macro)
    macro_mock.name = "Test Macro"

    model.add_macro(macro_mock)

    assert model.rowCount(QModelIndex()) == 1
    assert model.data(model.index(0, 0), Qt.DisplayRole) == "Test Macro"


def test_macro_table_model_remove_macro(mocker: "MockerFixture") -> None:
    model = MacroTableModel()
    macro_mock_1 = mocker.Mock(spec=Macro)
    macro_mock_1.name = "Macro 1"
    macro_mock_2 = mocker.Mock(spec=Macro)
    macro_mock_2.name = "Macro 2"

    model.add_macro(macro_mock_1)
    model.add_macro(macro_mock_2)

    assert model.rowCount(QModelIndex()) == 2

    model.remove_macro(0)

    assert model.rowCount(QModelIndex()) == 1
    assert model.data(model.index(0, 0), Qt.DisplayRole) == "Macro 2"


def test_macro_table_model_header_data() -> None:
    model = MacroTableModel()

    assert model.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "Macro"
    assert model.headerData(0, Qt.Vertical, Qt.DisplayRole) == QVariant()
    assert model.headerData(0, Qt.Horizontal, Qt.TextAlignmentRole) == Qt.AlignLeft


def test_macro_table_model_data_invalid_index() -> None:
    model = MacroTableModel()

    invalid_index = QModelIndex()
    assert model.data(invalid_index, Qt.DisplayRole) == QVariant()


def test_macro_table_model_data_text_alignment(mocker: "MockerFixture") -> None:
    model = MacroTableModel()
    macro_mock = mocker.Mock(spec=Macro)
    macro_mock.name = "Macro for Alignment"

    model.add_macro(macro_mock)

    index = model.index(0, 0)

    assert model.data(index, Qt.TextAlignmentRole) == Qt.AlignLeft


def test_macro_table_model_data_tooltip_role(mocker: "MockerFixture") -> None:
    model = MacroTableModel()
    macro_mock = mocker.Mock(spec=Macro)
    macro_mock.name = "Tooltip Macro"

    model.add_macro(macro_mock)

    index = model.index(0, 0)

    assert model.data(index, Qt.ToolTipRole) == "Tooltip Macro"
