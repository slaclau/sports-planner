import os
import sys
from pathlib import Path

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Sports Planner"
copyright = "2023-2024, Sebastien Laclau"
author = "Sebastien Laclau"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.graphviz",
    "sphinx_pyreverse",
    #    "numpydoc",
]

autosummary_generate = True


autodoc_default_options = {
    "undoc-members": True,
}
autoclass_content = "class"
# autodoc_class_signature = "separated"
autodoc_member_order = "bysource"
autodoc_docstring_signature = True
autodoc_mock_imports = []
autodoc_typehints = "description"

templates_path = ["_templates"]
exclude_patterns = []

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "gi.repository": ("https://amolenaar.pages.gitlab.gnome.org/pygobject-docs", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "plotly": ("https://plotly.com/python-api-reference/", None),
}

inheritance_graph_attrs = dict(rankdir="TB", size='""')

graphviz_output_format = "svg"

sys.path.insert(0, str(Path("..", "..", "src").resolve()))

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = 'default'
html_theme = "pydata_sphinx_theme"
# html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_extra_path = ["prebuilt"]

html_theme_options = {
    "logo": {
        "image_light": "icon.png",
        "image_dark": "icon.png",
    }
}
