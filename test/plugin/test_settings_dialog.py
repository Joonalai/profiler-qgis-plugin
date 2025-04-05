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

from typing import TYPE_CHECKING, Any, Callable

import pytest
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLineEdit,
    QSpinBox,
    QWidget,
)

from profiler_plugin.ui.settings_dialog import SettingsDialog
from qgis_profiler.settings import ProfilerSettings

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


@pytest.fixture
def settings_dialog(qtbot: "QtBot") -> "SettingsDialog":
    dialog = SettingsDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    return dialog


def test_settings_dialog_initialization(settings_dialog: "SettingsDialog") -> None:
    assert settings_dialog.combo_box_log_level_file.count() > 0
    assert settings_dialog.combo_box_log_level_console.count() > 0
    assert settings_dialog.combo_box_log_level_file.currentText() in [
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ]
    assert settings_dialog.combo_box_log_level_console.currentText() in [
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ]

    assert len(settings_dialog._widgets) == len(ProfilerSettings)
    assert set(settings_dialog._widgets.keys()) == set(ProfilerSettings)
    # utils.wait(10000)


@pytest.mark.parametrize(
    (
        "setting_key",
        "expected_widget",
        "get_value_function",
        "test_value",
        "set_value_function",
    ),
    [
        (
            "active_group",
            QLineEdit,
            "text",
            "test",
            lambda widget, value: widget.setText(value),
        ),
        (
            "profiler_enabled",
            QCheckBox,
            "isChecked",
            False,
            lambda widget, value: widget.setChecked(value),
        ),
        (
            "normal_time",
            QDoubleSpinBox,
            "value",
            1.23,
            lambda widget, value: widget.setValue(value),
        ),
        (
            "process_event_count",
            QSpinBox,
            "value",
            10,
            lambda widget, value: widget.setValue(value),
        ),
    ],
)
def test_settings_dialog_widget_configuration(
    settings_dialog: "SettingsDialog",
    setting_key: str,
    expected_widget: QWidget,
    test_value: Any,
    get_value_function: str,
    set_value_function: Callable[[QWidget, Any], None],
    qtbot: "QtBot",
) -> None:
    setting = ProfilerSettings[setting_key]

    widget = settings_dialog._widgets.get(setting)
    assert widget is not None
    assert isinstance(widget, expected_widget)

    assert getattr(widget, get_value_function)() == setting.value.default
    assert setting.get() == setting.value.default

    set_value_function(widget, test_value)
    qtbot.wait(1)

    assert setting.get() == test_value


def test_reset_settings_dialog(
    settings_dialog: "SettingsDialog", qtbot: "QtBot"
) -> None:
    widget = settings_dialog._widgets.get(ProfilerSettings.profiler_enabled)
    assert isinstance(widget, QCheckBox)
    assert widget.isChecked()
    assert ProfilerSettings.profiler_enabled.get() is True

    widget.setChecked(False)
    qtbot.wait(1)

    assert ProfilerSettings.profiler_enabled.get() is False

    qtbot.mouseClick(
        settings_dialog.button_box.button(QDialogButtonBox.Reset), Qt.LeftButton
    )
    qtbot.wait(1)

    widget = settings_dialog._widgets.get(ProfilerSettings.profiler_enabled)
    assert isinstance(widget, QCheckBox)
    assert widget.isChecked()
