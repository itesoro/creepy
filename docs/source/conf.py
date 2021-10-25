import os

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


# -- Project information -----------------------------------------------------

project = os.environ['PROJECTNAME']
copyright = '2021, Tesoro'
author = 'Tesoro'

# The full version, including alpha/beta/rc tags
version = '0.1.0'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'numpydoc',
    'sphinx.ext.intersphinx',
    'autoapi.extension',
    'myst_parser',
    'sphinx.ext.doctest'
]


intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'numpy': ('https://numpy.org/doc/stable', None),
    'torch': ('https://pytorch.org/docs/stable/', None),
    'pandas': ('https://pandas.pydata.org/docs/', None),
}


# Autoapi configuration
autoapi_type = 'python'
autoapi_dirs = [os.path.relpath(os.environ['CODEDIR'], os.environ['SOURCEDIR'])]
autoapi_ignore = ["*/tests/*"]
autoapi_options = ['members', 'undoc-members', 'show-inheritance', 'show-module-summary',
                   'special-members', 'imported-members']  # `private-members` is removed.
autoapi_root = os.path.relpath(os.environ['AUTOAPIDIR'], os.environ['SOURCEDIR'])
autoapi_keep_files = False  # Set to `True` if you want to switch to manual docs.
autoapi_template_dir = 'autoapi_templates'


# Create jinja test that checks if the file exists
def local_file(name):
    path = os.path.join(os.environ['SOURCEDIR'], name.lstrip('/'))
    return os.path.exists(path)


def _prep_jinja_env(jinja_env):
    jinja_env.tests['loc_file'] = local_file


autoapi_prepare_jinja_env = _prep_jinja_env


# Show member name without full path
add_module_names = False


def skip_slots(app, what, name, obj, skip, options):
    if "__slots__" in name:
        return True
    return None


def setup(sphinx):
    sphinx.connect("autoapi-skip-member", skip_slots)


source_suffix = ['.rst', '.md']


# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'pydata_sphinx_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']
