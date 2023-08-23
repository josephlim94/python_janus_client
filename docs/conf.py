# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys

sys.path.insert(0, os.path.abspath(".."))


# -- Project information -----------------------------------------------------

project = "Janus Client"
copyright = "2021, Lim Meng Kiat"
author = "Lim Meng Kiat"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "alabaster"

html_sidebars = {
    "**": [
        "about.html",
        "navigation.html",
        "relations.html",
        "searchbox.html",
        "donate.html",
    ]
}

html_theme_options = {
    "description": "Janus WebRTC gateway Python asyncio client",
    "canonical_url": "https://janus-client-in-python.readthedocs.io/",
    "github_user": "josephlim94",
    "github_repo": "janus_gst_client_py",
    "github_button": True,
    "github_type": "star",
    "github_banner": True,
    # "badges": [
    #     {
    #         "image": "https://img.shields.io/badge/License-MIT-yellow.svg",
    #         "target": "https://opensource.org/licenses/MIT",
    #         "height": "20",
    #         "alt": "License: MIT",
    #     },
    #     {
    #         "image": "https://img.shields.io/badge/Stage-ALPHA-orange.svg",
    #         # "target": f"https://badge.fury.io/py/{project}",
    #         "height": "20",
    #         "alt": "Development Stage",
    #     },
    #     {
    #         "image": "https://readthedocs.org/projects/janus-client-in-python/badge/?version=latest",
    #         "target": "https://janus-client-in-python.readthedocs.io/en/latest/?badge=latest",
    #         "height": "20",
    #         "alt": "Documentation Status",
    #     },
    #     {
    #         "image": "https://img.shields.io/badge/coverage-80%25-green",
    #         # "target": f"https://codecov.io/github/{github_repo_slug}",
    #         "height": "20",
    #         "alt": "Code coverage status",
    #     },
    # ],
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
