# checkstyle: noqa
from datetime import datetime, timedelta

from twitter.common import log
from twitter.ops.database import DatabaseOps
from twitter.stressdash import config
from twitter.stressdash.ui.time_util import convert_utc_pst

import yaml
from sqlalchemy import (
  Boolean,
  Column,
  DateTime,
  ForeignKey,
  Integer,
  String,
  Text,
)
from sqlalchemy.orm import relationship


db = DatabaseOps(pool_size=config.SQL_POOLSIZE,
                 pool_timeout=config.SQL_POOLTIMEOUT,
                 pool_recycle=config.SQL_POOLRECYCLE,
                 sql_echo=config.SQL_ECHO)


class Features(db.Base):
  """
  Holds all entries for features
  """

  name = Column(String(255), unique=True, nullable=False)
  weekly_max_rps = Column(Integer, default=0, nullable=True)  # max for the past 7 days (TODO: automate)
  yearly_max_rps = Column(Integer, default=0, nullable=True)  # max for the past 12 months
  max_tested_rps = Column(Integer, default=0, nullable=True)  # max ever done during testing
  target_rps = Column(Integer, default=0, nullable=True)  # what we hope to reach this year during testing
  highest_recorded_rps = Column(Integer, default=0, nullable=True)  # most the feature has ever reached
  dashboard_slugs = Column(String(1500), nullable=True)  # the viz dashboard slug names, comma-separated
  rps_query = Column(String(1500), nullable=True)  # cuckoo query to get current rps
  tests = relationship('Tests', cascade='all, delete-orphan')
  corvus_name = Column(String(255), nullable=True)  # the corvus alias for this feature
  # TODO(klaplante): allow to upload custom templates instead of using the predefined one
  pcm_template = Column(Text, nullable=True)  # custom pcm yml template

  @property
  def current_year_max_rps(self):
    year = datetime.utcnow().year
    current_year = [t for t in self.tests if t.ended_at.year == year]
    tests = [t.max_rps for t in current_year]
    if tests:
      return max(tests)
    return 0

  @property
  def max_total_rps(self):
    """
    Either the highest_recorded_rps or the max() of all tests max_rps
    """

    max_tested = self.max_tested_total_rps
    return max([max_tested, self.highest_recorded_rps, self.max_tested_rps])

  @property
  def max_tested_total_rps(self):
    """
    Either the given max_tested_rps or the max of our testing.

    We do this calculation here because when users are entering new features
    we allow them to specify this data because we dont already have it.
    Once that feature starts getting tested we override it.
    """

    max_tested = 0
    if len(self.tests) > 0:
      max_tested = max([t.max_rps for t in self.tests])
    return max([max_tested, self.max_tested_rps])

  @property
  def latest_test(self):
    """
    Returns the latest run test for this feature
    """

    return (Tests.search
            .filter(Tests.feature_id == self.id)
            .order_by(Tests.ended_at.desc())
            .first())

  @classmethod
  def get_by_name(cls, name):
    return cls.search.filter(cls.name == name).first()

  def get_test_by_id(self, test_id):
    tests = [t for t in self.tests if t.id == test_id]
    if len(tests) == 0:
      return None
    return tests[0]


class Tests(db.Base):
  """
  Holds all entries for stresstests
  """

  zone = Column(String(4), nullable=False)
  started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
  ended_at = Column(DateTime, nullable=False, default=datetime.utcnow)
  target_rps = Column(Integer, nullable=False)
  max_rps = Column(Integer, default=0, nullable=True)
  sustained_minutes = Column(Integer, default=0, nullable=True)
  jira_key = Column(String(100), nullable=True)
  successful = Column(Boolean(name='successful'), default=False, nullable=False)
  comment = Column(Text, nullable=True)
  feature_id = Column(Integer, ForeignKey('features.id'), nullable=False)
  snapshots = relationship('Snapshots', cascade='all, delete-orphan')

  @classmethod
  def recent(cls, days):
    date = datetime.utcnow() - timedelta(days=days)
    return cls.search.filter(cls.ended_at > convert_utc_pst(date))

  def get_snapshot(self, slug):
    return (Snapshots.search
            .filter(Snapshots.test_id == self.id)
            .filter(Snapshots.slug == slug)
            .first())


class Snapshots(db.Base):
  """
  Holds all snapshots
  """

  test_id = Column(Integer, ForeignKey('tests.id'), nullable=False)
  snapshot_id = Column(Integer, nullable=False)
  url = Column(String(255), nullable=False)
  slug = Column(String(255), nullable=False)


def db_init():
  # Read creds
  if not hasattr(config, 'MYSQL_USER') or not hasattr(config, 'MYSQL_PASS'):
    with open(config.TWKEYS, 'r') as cred_file:
      log.info('Using twkey: {}'.format(config.TWKEYS))
      creds = yaml.load(cred_file.read())
      config.MYSQL_USER = creds[config.MYSQL_CRED_PREFIX + 'username']
      config.MYSQL_PASS = creds[config.MYSQL_CRED_PREFIX + 'password']
  db.init_mysql_db(db=config.MYSQL_DB,
                   host=config.MYSQL_HOST,
                   user=config.MYSQL_USER,
                   passwd=config.MYSQL_PASS)
