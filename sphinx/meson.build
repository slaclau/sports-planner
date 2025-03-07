sphinx_src = files()
subdir('source')

sphinx_xml = custom_target(
  input: sphinx_src,
  output: 'xml',
  command: ['sphinx-build', '-b', 'xml', meson.current_source_dir() / 'source', 'xml'],
)

if get_option('wheel')
  yelp_dir = py_installation.get_install_dir() / 'sports_planner' / 'help'
else
  yelp_dir = get_option('datadir') / 'help' / 'C' / 'sports-planner'
endif

yelp_xml = custom_target(
  input: sphinx_xml,
  output: 'index.docbook',
  command: ['rstxml2docbook', 'xml/userguide.xml', '-ns', '-o', '@OUTPUT@'],
  install: true,
  install_dir: yelp_dir
)
