from datetime import datetime, timedelta

from twitter.common import log
from twitter.common.concurrent import as_completed, ThreadPoolExecutor
from twitter.common_internal.decorators import retry
from twitter.stressdash import config
from twitter.stressdash.persistence.store import Store
from twitter.stressdash.ui.metrics_util import get_metrics
from twitter.stressdash.ui.time_util import convert_pst_utc

import requests


def callback_url(env):
  host = config.HTTP_URL.format(env)
  return '{}/cron/weekly_rps_callback'.format(host)


@retry(Exception)
def log_run(succeeded=0, failed=0, env='staging'):
  data = {'succeeded': succeeded, 'failed': failed}
  requests.post(callback_url(env), data=data)


def range_excludes(tests):
  excludes = []
  for test in tests:
    start = convert_pst_utc(test.started_at)
    end = convert_pst_utc(test.ended_at) + timedelta(minutes=10)
    excludes.append((start, end))
  return excludes


def now_delta(days):
  return datetime.now() - timedelta(days=days)


def run(feature_id, ranges):
  feature = Store.get_feature(feature_id)
  all_excludes = range_excludes(Store.get_recent_tests(7, feature.id))
  if not feature.rps_query:
    log.info('"{}" does not specify rps_query'.format(feature.name))
    return
  log.info('Fetching rps queries for "{}"'.format(feature.name))
  log.info(feature.rps_query)
  # for each day range get the minutely metrics for each zone,
  # sum the minutely metrics together for the combined zones
  # and take the max combined value for each day.
  daily_maxes = []
  for start, end in ranges:
    log.info('Start: {}, End: {}'.format(start, end))
    zones = []
    for zone in config.ZONES:
      zones.append(get_metrics(feature.rps_query, zone, start, end, all_excludes))
    daily_maxes.append(max([sum(x) for x in zip(*zones)]))
  weekly_max_rps = int(max(daily_maxes))
  log.info('Max for "{}": {}'.format(feature.name, weekly_max_rps))
  if weekly_max_rps != feature.weekly_max_rps:
    feature.weekly_max_rps = weekly_max_rps
    Store.save_feature(feature)


def weekly_rps_run(opts):
  succeeded = 0
  all_features = Store.all_features()
  ranges = [(now_delta(i + 1), now_delta(i)) for i in range(7)]

  with ThreadPoolExecutor(max_workers=config.MAX_THREADS) as ex:
    futures = [ex.submit(run, f.id, ranges) for f in all_features]
    for res in as_completed(futures):
      exc = res.exception()
      if exc is None:
        succeeded += 1
      else:
        log.error(exc)

  log_run(succeeded, len(all_features) - succeeded, opts.env)
