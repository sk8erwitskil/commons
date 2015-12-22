from twitter.common import log
from twitter.stressdash import config
from twitter.stressdash.persistence.store import Store
from twitter.stressdash.ui.time_util import adjust_time, convert_pst_utc

from flask import flash


def snapshot_name(name, test_id):
  return name.replace(' ', '_').lower() + str(test_id)


def snapshot_url(url):
  return config.SNAPSHOT_URL.format(url)


def delete_viz_snapshot(client, test, slug):
  snapshot = test.get_snapshot(slug)
  if snapshot is None: return  # no snapshot found
  try:
    client.delete_snapshot(snapshot.snapshot_id)
  except client.ClientError as e:
    # we do not want to stop here if we get an error
    # because we still want to remove the snapshot
    # instance from our test regardless if viz is
    # failing or not.
    error = 'Error deleting snapshot: {}'.format(e)
    flash(error)
    log.error(error)
  test.snapshots.remove(snapshot)
  Store.save_test(test)
  log.info('Deleted snapshot {}'.format(slug))
  return test.exc


def create_viz_snapshot(client, test, slug):
  delta = (60 * 30)
  data = client.store_snapshot(
    snapshot_name(slug, test.id),
    'Created by stressdash',
    slug,
    test.zone,
    adjust_time(convert_pst_utc(test.started_at), -delta),
    adjust_time(convert_pst_utc(test.ended_at), delta),
    config.ODS_GROUP)
  snapshot = Store.new_snapshot(test,
    snapshot_id=data['id'],
    url=snapshot_url(data['url']),
    slug=slug)
  log.info('Created new snapshot for {}'.format(slug))
  return snapshot
