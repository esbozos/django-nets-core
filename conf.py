project = 'Django NETS CORE'
copyright = '2016-2042, The Authors'
author = 'Norman Torres'
version = release = '1.0.0'

# -- General configuration ------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

exclude_patterns = [
    '_build',
    'Thumbs.db',
    '.DS_Store',
]
extensions = []
language = 'en'
master_doc = 'README'
pygments_style = 'sphinx'
source_suffix = '.rst'
templates_path = ['_templates']

# -- Options for HTML output ----------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']