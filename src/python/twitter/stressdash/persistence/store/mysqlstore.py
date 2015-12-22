from twitter.common import log
from twitter.stressdash.persistence.backend import mysql
from twitter.stressdash.persistence.store import base


class MysqlStore(base.BaseStore):
  def __init__(self, flask_app=None):
    log.info('Using mysql store')
    self.models = mysql
    self.models.db_init()
    if flask_app:
      log.info('Setting up flask teardown')
      self.models.db.create_flask_teardown(flask_app)

  def _save(self, item):
    log.debug('Persisting changes to {}'.format(item))
    return item.save()

  def _delete(self, item):
    log.info('Deleteing {}'.format(item))
    return item.delete()

  def get_feature(self, feature_id):
    return self.models.Features.get_by_id(feature_id)

  def get_test(self, test_id):
    return self.models.Tests.get_by_id(test_id)

  def delete_feature(self, feature):
    return self._delete(feature)

  def delete_test(self, test):
    return self._delete(test)

  def all_features(self):
    return self.models.Features.search.all()

  def new_feature(self, *args, **kwargs):
    feature = self.models.Features(*args, **kwargs)
    # make sure we dont try to create a new one with same name
    existing = self.models.Features.get_by_name(feature.name)
    if existing:
      feature.exc = 'Feature with name {} already exists!'.format(feature.name)
    else:
      self.save_feature(feature)
    return feature

  def new_test(self, feature, *args, **kwargs):
    try:
      test = self.models.Tests(*args, **kwargs)
      feature.tests.append(test)
      self.save_feature(feature)
      test.exc = feature.exc
    except TypeError as e:
      test = self.models.Tests()
      test.exc = e
    return test

  def save_feature(self, feature):
    return self._save(feature)

  def save_test(self, test):
    return self._save(test)

  def get_recent_tests(self, days, feature_id=None):
    alltests = self.models.Tests.recent(days)
    if feature_id:
      return alltests.filter(self.models.Tests.feature_id == feature_id)
    return alltests

  def new_snapshot(self, test, *args, **kwargs):
    try:
      snapshot = self.models.Snapshots(*args, **kwargs)
      test.snapshots.append(snapshot)
      self.save_test(test)
      snapshot.exc = test.exc
    except TypeError as e:
      snapshot = self.models.Snapshots()
      snapshot.exc = e
    return snapshot
