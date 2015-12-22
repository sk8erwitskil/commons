from twitter.common import log
from twitter.ops.observability.metrics import Metric
from twitter.stressdash.ui.time_util import datetime_int


def ts_valid(ts, start, end):
  return (ts < datetime_int(start)) or (ts > datetime_int(end))


def get_metrics(query, zone, start, end, excludes=[]):
  log.info('Start: {}, End: {}'.format(start, end))
  metric = Metric.metric_from_query_str(
    query,
    zone=zone,
    start=datetime_int(start),
    end=datetime_int(end))
  metrics = metric.query_results[0]['data']
  for tstart, tend in excludes:
    log.info('Excluding {} to {}'.format(tstart, tend))
    filtered = [(ts, m) for ts, m in metrics if ts_valid(ts, tstart, tend)]
    diff = len(metrics) - len(filtered)
    if diff > 0:
      log.info('Filtered {} metrics'.format(diff))
    metrics = filtered
  return [m[1] for m in metrics]
