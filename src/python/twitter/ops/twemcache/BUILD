python_library(
  name = 'twemcache',
  sources = globs('*.py'),
  dependencies = [
    ':pymemcached',
    'src/python/twitter/common/concurrent',
    'src/python/twitter/common/log',
    'src/python/twitter/common_internal/zookeeper:tunneler',
    'src/python/twitter/common_internal/zookeeper:twitter_serverset_kazoo',
  ]
)

# for threading support
python_requirement_library(
  name = 'pymemcached',
  requirements = [
    python_requirement('pymemcache==1.3.5'),
  ]
)
