from __future__ import unicode_literals

from twitter.ops.database.mixin import DefaultMixin

from sqlalchemy import create_engine, event, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import Pool
# checkstyle: noqa


class DatabaseOps(object):
  """
  Interact with a database.

  The proper usage is to create all your models as
  subclasses of the `Base` attribute of this class.
  See the example below. Once you have all your models
  you can run an init method to create your ORM.

  Example:
  from twitter.ops.database import DatabaseOps
  from sqlalchemy import Column, String
  # create an instance
  db = DatabaseOps()
  # create all your models before running any init method
  class Users(db.Base):
    name = Column(String(255), unique=True)
    email = Column(String(255), unique=True)
  # once your models are created and imported run your init method
  db.init_mysql_db('localhost', 'dbname', 'user', 'pass')
  user = Users(name='Kyle Laplante', email='klaplante@twitter.com')
  # models have a .save() method to persist to the DB
  user.save()
  # models have a .search() method which is the same as the sqlalchemy .query() method
  Users.search.filter(Users.name == 'Kyle Laplante').first()
  # models have a .delete() method to remove from the DB
  user.delete()

  # To create a sqlite db simply use this method
  db.create_sqlite_db()
  """

  Base = declarative_base(cls=DefaultMixin)

  def __init__(self, pool_size=20, pool_timeout=15, pool_recycle=3600, sql_echo=False):
    self._pool_size = pool_size
    self._pool_timeout = pool_timeout
    self._pool_recycle = pool_recycle
    self._sql_echo = sql_echo

  def init_sqlite_db(self, location=None):
    """
    Creates a sqlite db engine.

    If location is None will create an in memory db.
    """

    return self.init_db(
        create_engine('sqlite:///{}'.format(location or ''))
    )

  def init_mysql_db(self, host, db, user, passwd):
    """
    Creates a mysql db engine
    """

    engine_string = 'mysql+pymysql://{}:{}@{}/{}'.format(
        user, passwd, host, db)
    engine = create_engine(engine_string,
                           pool_size=self._pool_size,
                           pool_timeout=self._pool_timeout,
                           pool_recycle=self._pool_recycle,
                           echo=self._sql_echo)
    return self.init_db(engine)

  def init_db(self, engine):
    """
    Initializes the engine and creates the tables
    """

    self.engine = engine
    self.session = scoped_session(
        sessionmaker(autocommit=False, autoflush=True, bind=self.engine)
    )
    self.Base.search = self.session.query_property()
    self.Base._session = self.session
    self.Base.metadata.create_all(bind=self.engine)

  def create_flask_teardown(self, flask_app):
    """
    Creates the teardown method for resetting the
    session after each request in a flask app.

    Only call after init'ing a DB.
    """

    @flask_app.teardown_appcontext
    def shutdown_session(exception=None):
      self.session.remove()

  def create_ping_connection(self):
    """
    Creates a listener for pool checkouts to make
    sure the connection we are about to use is valid.
    """

    @event.listens_for(Pool, 'checkout')
    def ping_connection(dbapi_connection, connection_record, connection_proxy):
      cursor = dbapi_connection.cursor()
      try:
        cursor.execute('SELECT 1')
      except:  # noqa
        # optional - dispose the whole pool
        # instead of invalidating one at a time
        # connection_proxy._pool.dispose()
        # raise DisconnectionError - pool will try
        # connecting again up to three times before raising.
        raise exc.DisconnectionError()
      cursor.close()
