from datetime import datetime
from tempfile import NamedTemporaryFile

from twitter.common import log
from twitter.stressdash import config
from twitter.stressdash.ui import flask_app
from twitter.stressdash.ui.time_util import convert_pcm_time

from flask import flash, Markup, request


class TestCandidate(object):
  def __init__(self, dc, qps_per_batch, planned_start):
    self.dc = dc
    self.qps_per_batch = qps_per_batch
    self.planned_start = convert_pcm_time(planned_start)
    if hasattr(request, 'elfowl_cookie'):
      self.current_user = request.elfowl_cookie.user
    else:
      self.current_user = 'unknown'
    log.info('PCM user: {}'.format(self.current_user))


def generate_yml(feature, test):
  env = flask_app.config['services']['jinja_env']
  if feature.pcm_template:
    tmpl = env.from_string(feature.pcm_template)
  else:
    tmpl = env.get_template('pcm.yml')
  config = tmpl.render(feature=feature, this=test)
  with NamedTemporaryFile(delete=False) as fp:
    fp.write(config)
    return fp.name


def pcm_link(key):
  link = 'https://jira.twitter.biz/browse/{}'.format(key)
  return Markup('Created PCM <a href="{}">{}</a>'.format(link, key))


def create_pcm(feature, dc, qps_per_batch, start_time):
  client = flask_app.config['services']['get_pcm']()
  planned_start = datetime.strptime(start_time, config.LOCAL_TIME_FMT)
  path = generate_yml(feature, TestCandidate(dc, qps_per_batch, planned_start))
  log.info('Created temp pcm yml: {}'.format(path))
  try:
    pcm = client.create_from_file(path)
    log.info('Created PCM {}'.format(pcm.key))
    flash(pcm_link(pcm.key), 'success')
  except client.PCMError as e:
    log.error(e)
    flash('Error creating pcm: {}'.format(e), 'danger')
    return str(e)
