from twitter.common import log

from twitter.ops.observability.vizurl_client import generate_url
from twitter.stressdash.ui import flask_app


@flask_app.template_filter('num_fmt')
def num_fmt(num):
  try:
    return format(num, ',d')
  except ValueError:
    log.error('Unable for format {}'.format(num))
    return num


@flask_app.template_filter('rps_link')
def rps_link(query):
  queries = {
    'RPS smf1': {'query': query, 'dc': 'smf1'},
    'RPS atla': {'query': query, 'dc': 'atla'},
  }
  return generate_url(queries)
