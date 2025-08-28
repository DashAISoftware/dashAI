import os
import sys

MOCK_IN_CI = os.getenv("BUILDING_DOCS") == "1"  # o CI/READTHEDOCS

# Get the directory of conf.py (e.g. /home/ctamblay/CENIA/DashAI/docs/source)
conf_dir = os.path.dirname(os.path.realpath(__file__))

# The repository root is two directories up (i.e. /home/ctamblay/CENIA/DashAI)
repo_root = os.path.abspath(os.path.join(conf_dir, os.pardir, os.pardir))
print("conf_dir:", conf_dir)  # Debug: prints conf.py directory
print("repo_root:", repo_root)  # Debug: should print the repository root

# Insert the repository root into sys.path so that modules can be imported
sys.path.insert(0, repo_root)

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "DashAI"
copyright = "2022, Felipe Bravo-Marquez"
author = "Felipe Bravo-Marquez"
release = "0.0.4"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.autosummary",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.githubpages",
    "sphinx_rtd_theme",
    "sphinx_design",
]
autosummary_generate = True
add_module_names = False
templates_path = ["_templates"]
exclude_patterns = []

if MOCK_IN_CI:
    autodoc_mock_imports = [
        "llama_cpp",
        "llama_cpp_python",
        "llama_cpp_cuda",
        "torch",
        "tensorflow",
    ]
else:
    autodoc_mock_imports = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_static_path = [
    "_static",
    "_images",
]

html_theme = "sphinx_rtd_theme"
html_logo = "_static/logo.png"
html_favicon = "_static/favicon.ico"


html_theme_options = {
    "logo_only": True,
}
