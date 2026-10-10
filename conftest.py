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

"""Shared pytest configuration for all components."""

from collections.abc import Iterator
from os.path import normpath
from pathlib import Path

import pytest
from qgis_plugin_tools.tools import resources

import profiler_plugin

PLUGIN_DIR = Path(profiler_plugin.__file__).parent


@pytest.fixture(scope="session", autouse=True)
def _resolve_plugin_path_to_profiler_plugin() -> Iterator[None]:
    """Resolve the qgis_plugin_tools plugin path to profiler_plugin in all tests.

    qgis_plugin_tools finds the plugin by walking the call stack for a plugin
    package or by scanning the imported modules for one. Test modules and
    qgis_profiler are not inside profiler_plugin, so calls made from them
    (e.g. Settings.reset()) would otherwise fail to resolve the plugin, or
    resolve to another one and use a different QSettings section than the
    plugin code under test.
    """
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            resources,
            "plugin_path",
            lambda *args: normpath(PLUGIN_DIR.joinpath(*args)),
        )
        if (plugin_name := resources.plugin_name()) != "Profiler":
            msg = f"Plugin resolved to {plugin_name!r} instead of Profiler"
            raise RuntimeError(msg)
        yield
