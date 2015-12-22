import inspect

from twitter.common.lang import Singleton
from twitter.stressdash.persistence.store import base


class StoreHolder(Singleton):
  """
  Holder that will be used to make all calls to
  underlying data store
  """

  def _set_store(self, store):
    """
    Sets up this class to talk to the given data store

    Adds all members of the `store` to this class
    """

    if not isinstance(store, base.BaseStore):
      raise ValueError('{} is not of type BaseStore'.format(store))
    self.__dict__.update(dict(inspect.getmembers(store)))

  def use_mysql(self, flask_app=None):
    """
    Use mysql as the backend data store

    optionally pass in a flask app to setup the
    teardown method
    """

    # import here so we dont needlessly init the tables
    # when using other stores
    from twitter.stressdash.persistence.store.mysqlstore import MysqlStore
    self._set_store(MysqlStore(flask_app))


Store = StoreHolder()
