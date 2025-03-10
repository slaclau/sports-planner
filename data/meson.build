desktop_file = i18n.merge_file(
        input: 'io.github.slaclau.sports-planner.desktop.in',
       output: 'io.github.slaclau.sports-planner.desktop',
         type: 'desktop',
       po_dir: '../po',
      install: true,
  install_dir: get_option('datadir') / 'applications'
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils, args: [desktop_file])
endif

py_installation = python.find_installation()

c = run_command('find_gschemas.sh', check: true)
schemas = c.stdout().strip().split('\n')

if get_option('wheel')
  install_data(schemas,
    install_dir: py_installation.get_install_dir() / 'sports_planner' / 'data',
  )
else
  install_data(schemas,
    install_dir: get_option('datadir') / 'glib-2.0' / 'schemas'
  )
endif

compile_schemas = find_program('glib-compile-schemas', required: false, disabler: true)
test('Validate schema file',
     compile_schemas,
     args: ['--strict', '--dry-run', meson.current_source_dir()])

pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'test'


if get_option('wheel')
  gnome.compile_resources('resources',
    'resources.gresource.xml',
    gresource_bundle: true,
    install: true,
    install_dir: pkgdatadir,
  )
else
  gnome.compile_resources('resources',
    'resources.gresource.xml',
    gresource_bundle: true,
    install: true,
    install_dir: py_installation.get_install_dir() / 'sports_planner' / 'data',
  )
endif
