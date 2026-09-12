# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""Configuration of the Sphinx documentation."""

from __future__ import annotations

from importlib.metadata import version as get_version
from os import environ

project = "gemseo-algos-lab"
author = "Simone Coniglio"
copyright = "2026, Simone Coniglio"  # noqa: A001
release = get_version("gemseo-algos-lab")
version = ".".join(release.split(".")[:2])

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_design",
]

myst_enable_extensions = ["dollarmath", "amsmath", "colon_fence", "deflist"]
myst_heading_anchors = 3

autosummary_generate = True
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "member-order": "bysource",
}
autodoc_typehints = "description"
napoleon_google_docstring = True
napoleon_numpy_docstring = False

# Fetching the inventories requires network access, and their failure cannot be
# suppressed, so it would fail a -W build offline. They are enabled explicitly,
# by the workflow that publishes the documentation.
intersphinx_mapping = (
    {
        "python": ("https://docs.python.org/3", None),
        "numpy": ("https://numpy.org/doc/stable", None),
        "scipy": ("https://docs.scipy.org/doc/scipy", None),
        "gemseo": ("https://gemseo.readthedocs.io/en/stable", None),
    }
    if environ.get("SPHINX_INTERSPHINX") == "1"
    else {}
)
intersphinx_disabled_reftypes = ["*"]
intersphinx_timeout = 10

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_static_path = ["_static"]
html_title = f"gemseo-algos-lab {release}"
html_logo = "_static/monogram.png"
html_theme_options = {
    "source_repository": "https://github.com/SimoneConiglio/Optimization-algorithms/",
    "source_branch": "main",
    "source_directory": "docs/",
}

nitpicky = False
# The inventories are unreachable when building without network access,
# which must not fail a -W build.
suppress_warnings = ["myst.header"]
