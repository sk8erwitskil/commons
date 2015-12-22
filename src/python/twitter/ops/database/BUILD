# for gevent support
python_requirement_library(
  name = 'sqlalchemy',
  requirements = [
    python_requirement('SQLAlchemy==1.0.8'),
  ]
)

# for gevent support
python_requirement_library(
  name = 'pymysql',
  requirements = [
    python_requirement('PyMySQL==0.6.6'),
  ]
)

python_library(
  name = 'database',
  sources = globs('*.py'),
  dependencies = [
    ':pymysql',
    ':sqlalchemy',
    'src/python/twitter/common/log',
  ]
)
