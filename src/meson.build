sources = run_command(['find', '.', '-name', '*.py'], check: true).stdout().strip().replace('./', '').split('\n')

py_installation = python.find_installation()
py_installation.install_sources(
  sources,
  preserve_path: true,
)

subdir('sports_planner')