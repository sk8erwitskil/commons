from __future__ import unicode_literals
import decimal
from datetime import datetime

from twitter.common import log

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm.collections import InstrumentedList
# checkstyle: noqa


class DefaultMixin(object):
  """
  Parent class containing standard attributes to be inherited by all models
  """

  _NO_SERIALIZE = []
  __table_args__ = {'mysql_charset': 'utf8', 'mysql_engine': 'InnoDB'}

  id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
  created_on = Column(DateTime, nullable=False, default=datetime.utcnow)
  updated_on = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

  def _all_attrs(self):
    """
    Get all attributes
    """

    return [(x, getattr(self, x)) for x in dir(self) if not x.startswith('_') and x != 'metadata']

  def _serialize(self, attr, val, current_depth, max_depth):
    """
    Serialize the attributes
    """

    if current_depth >= max_depth:
      return None

    if attr in self._NO_SERIALIZE or callable(val) or val is None:
      return None
    elif attr == 'id':
      return None
    elif attr == 'search':
      return None
    elif isinstance(val, DefaultMixin):
      return val.to_json(current_depth + 1, max_depth)
    elif isinstance(val, decimal.Decimal):
      return float(val)
    elif isinstance(val, str) or isinstance(val, int) or isinstance(val, unicode):
      return val
    elif isinstance(val, datetime):
      return val.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(val, InstrumentedList) or isinstance(val, list):
      newlist = []
      for i in val:
        serialized = self._serialize(attr, i, current_depth + 1, max_depth)
        if serialized:
          newlist.append(serialized)
      return newlist
    else:
      log.warning('Could not serialize {} of type {}'.format(
          val, type(val)))

  def __repr__(self):
    """
    Return string rep
    """

    return '<{}(id:{}, created_on:{})>'.format(
        self.__class__.__name__, self.id, self.created_on)

  @declared_attr
  def __tablename__(cls):
    return cls.__name__.lower()

  def to_json(self, current_depth=0, max_depth=20):
    """
    Return json representation
    """

    ret = {}
    for attr, val in self._all_attrs():
      serialized = self._serialize(attr, val, current_depth, max_depth)
      if serialized is not None:
        ret[attr] = serialized
    return ret

  @classmethod
  def get_by_id(cls, itemid):
    return cls.search.filter(cls.id == itemid).first()

  def safe_commit(self):
    try:
      self._session.commit()
      self.exc = None
      return True
    except SQLAlchemyError as e:
      self._session.rollback()
      self.exc = e
      log.info('Error committing {}: {}'.format(str(self), e))
      return False

  def save(self):
    """
    Persist the object to the DB

    Either returns True if the object was saved
    or returns False if there was an error and
    rolls back the transaction.
    """

    self._session.add(self)
    return self.safe_commit()

  def delete(self):
    """
    Deletes a row from the DB.
    """

    self._session.delete(self)
    return self.safe_commit()
