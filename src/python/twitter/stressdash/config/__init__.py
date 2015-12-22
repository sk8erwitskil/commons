import os
import re
import sys


# Default config values
DEFAULTS = {
  'HOST': '0.0.0.0',
  'PORT': 1337,
  'DATA_DIR': os.path.join(os.path.sep, 'var', 'tmp', 'stressdash'),
  'ENABLE_AUTHENTICATION': True,
  'ENABLE_LOGLENS': False,
  'ELFOWL_AUTH_DOMAIN': 'dev.localhost',
  'HIPCHAT_ROOM': 'bot test 2',
  'SECRET_KEY': '71(+68tu&_1a_*04!vjmpy+^ey2&%h6q8=aykp270+jk1mdjj4',
  'SQL_ECHO': False,
  'SQL_POOLSIZE': 50,
  'SQL_POOLRECYCLE': 30,
  'SQL_POOLTIMEOUT': 10,
  'MYSQL_HOST': 'localhost:3306',
  'MYSQL_DB': 'stressdash_dev',
  'AUTHORIZED_USERS': [],
  'AUTHORIZED_GROUPS': ['perm-employee-group'],
  'LOGLENS_INDICES': 'stressdash_staging',
  'JIRA_TIME_FMT': '%Y-%m-%dT%H:%M:%S.000+0000',
  'LOCAL_TIME_FMT': '%Y-%m-%d %H:%M:%S',
  'JIRA_DESC_REGEX': re.compile(
      '\<\<stresstest_stats\>\>(?P<text>.*)\<\<stresstest_stats\>\>',
      re.DOTALL),
  'PCM_STATUSES': [
    '"closed"',
    '"resolved"',
    '"cancelled"',
    '"reviewable"',
    '"Peer Reviewable"',
    '"Post Mortem"',
  ],
  'PCM_COMPONENT': '(CRT.stresstest_testing)',
  'PCM_LABELS': '(whatshappening)',
  'RUNNING_TESTS_TTL': 30,
  'API_VER': 'v1',
  'ODS_GROUP': 'reliability-testing',
  'SNAPSHOT_URL': 'https://observe.twitter.biz/viz/snapshots/{}',
  'ZONES': ['smf1', 'atla'],
  'HTTP_URL': 'https://stressdash-{}-stresstest.service.smf1.twitter.biz',
  'MAX_THREADS': 50,
  'DEFAULT_CACHE_TTL': 60 * 60,
}


class Config(dict):
  """
  A class to store config values in. Inherits from dict, and provides access to keys
  via attributes.
  """

  def __init__(self, *args, **kwargs):
    super(self.__class__, self).__init__(*args, **kwargs)
    self.__dict__ = self  # magic

  def load_env(self, env):
    # Do required imports here due to our import override
    import os
    from twitter.common import log
    from pkg_resources import resource_string
    filepath = os.path.join('config', '{}.yml'.format(env))
    contents = resource_string('twitter.stressdash', filepath)
    log.info('Loaded config env: {}'.format(env))
    self.load_file(contents)

  def load_file(self, file_contents):
    # Do required imports here due to our import override
    from twitter.common import log
    import yaml

    settings = yaml.load(file_contents)
    log.debug('Loaded settings:\n%s' % settings)

    # Update the local config with the settings
    self.update(settings)


sys.modules[__name__] = Config(**DEFAULTS)
