# checkstyle: noqa
from abc import ABCMeta, abstractmethod


class BaseStore(object):
  """
  Implements a store for stressdash
  """

  __metaclass__ = ABCMeta

  @abstractmethod
  def all_features(self):
    """
    Returns all the known features
    """

  @abstractmethod
  def new_feature(self, *args, **kwargs):
    """
    Adds a new feature
    """

  @abstractmethod
  def new_test(self, feature, *args, **kwargs):
    """
    Adds a new test to the given feature
    """

  @abstractmethod
  def save_feature(self, feature):
    """
    Saves any modifications to the given feature
    """

  @abstractmethod
  def save_test(self, test):
    """
    Saves any modifications to the given test
    """

  @abstractmethod
  def get_feature(self, feature_id):
    """
    Returns a feature given the feature_id
    """

  @abstractmethod
  def delete_feature(self, feature):
    """
    Deletes the given feature
    """
