#  Copyright (c) 2026 profiler-qgis-plugin contributors.
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

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from pathlib import Path

# Add source directories to sys.path for autodoc
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root / "docs"))
sys.path.insert(0, str(_root / "components" / "core" / "src"))
sys.path.insert(0, str(_root / "components" / "plugin" / "src"))

# Install QGIS/PyQt stubs before any project imports
from _qgis_stubs import install_stubs  # noqa: E402

install_stubs()

project = "QGIS Profiler Plugin"
copyright = "2025-2026, profiler-qgis-plugin contributors"
author = "profiler-qgis-plugin contributors"
release = "0.0.1"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_parser",
    "sphinx_copybutton",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "DEVELOPMENT.md"]

# Support both rst and md
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# -- Autodoc configuration ---------------------------------------------------

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "exclude-members": "__weakref__",
}

# Napoleon settings (for Google/NumPy style docstrings)
napoleon_google_docstrings = True
napoleon_numpy_docstrings = False

# -- MyST-Parser configuration -----------------------------------------------

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]
myst_heading_anchors = 3

# Suppress warnings for relative links in MD files that work on GitHub
# but can't be resolved by Sphinx (e.g. ../src, ../requirements.txt)
suppress_warnings = ["myst.xref_missing"]

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_theme_options = {
    "navigation_depth": 3,
    "collapse_navigation": False,
}
