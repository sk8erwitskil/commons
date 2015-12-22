python_binary(name = 'stressdash',
  source = 'ui/server.py',
  dependencies = [
    'src/python/twitter/common/app',
    'src/python/twitter/common/log',
    'src/python/twitter/stressdash/ui',
  ]
)

python_library(name = 'stressdash_lib',
  sources = globs('*.py'),
  dependencies = [
    'src/python/twitter/common/log',
    'src/python/twitter/stressdash/config',
    'src/python/twitter/stressdash/persistence',
  ],
)
