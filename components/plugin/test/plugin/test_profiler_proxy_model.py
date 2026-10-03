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

import time
from typing import TYPE_CHECKING

import pytest
from qgis_profiler.settings import Settings

from profiler_plugin.ui.profiler_proxy_model import ProfilerProxyModel

if TYPE_CHECKING:
    from qgis_profiler.profiler import ProfilerWrapper

GROUP = "Proxy model group"


@pytest.fixture
def proxy_model(profiler: "ProfilerWrapper") -> ProfilerProxyModel:
    Settings.show_events_threshold.set(0.01)
    proxy_model = ProfilerProxyModel(profiler.item_model())
    proxy_model.set_group(GROUP)
    return proxy_model


def _row_names(proxy_model: ProfilerProxyModel) -> list[str]:
    return [proxy_model.index(row, 0).data() for row in range(proxy_model.rowCount())]


def test_added_record_should_be_shown_immediately(
    profiler: "ProfilerWrapper", proxy_model: ProfilerProxyModel
) -> None:
    # Act
    profiler.add_record("record", GROUP, 1.0)

    # Assert
    assert _row_names(proxy_model) == ["record"]


def test_added_record_below_threshold_should_be_hidden(
    profiler: "ProfilerWrapper", proxy_model: ProfilerProxyModel
) -> None:
    # Act
    profiler.add_record("record", GROUP, 0.001)

    # Assert
    assert _row_names(proxy_model) == []


def test_ended_event_should_be_shown_immediately(
    profiler: "ProfilerWrapper", proxy_model: ProfilerProxyModel
) -> None:
    # Act
    profiler.start("event", GROUP)
    profiler.add_record("record", GROUP, 1.0)
    time.sleep(0.02)
    profiler.end(GROUP)

    # Assert
    assert _row_names(proxy_model) == ["event"]
    event_index = proxy_model.index(0, 0)
    assert proxy_model.rowCount(event_index) == 1
    assert proxy_model.index(0, 0, event_index).data() == "record"
