import getpass
import os
import socket
import time
from logging import getLogger

from twitter.common import app, log
from twitter.common.metrics import AtomicGauge, LambdaGauge, RootMetrics
from twitter.common_internal.flask.extensions.trace import HTTPStatusStats
from twitter.common_internal.keybird import KeyBird
from twitter.common_internal.log.loglens_handler import LogLensHandler
from twitter.common_internal.pcm import PCM
from twitter.ops.observability.snapshot_client import SnapshotClient
from twitter.ops.jira import JiraOps
from twitter.ops.twemcache.client import TwemcacheClient
from twitter.stressdash import config
from twitter.stressdash.ui import flask_app
from twitter.stressdash.ui.context import *  # noqa
from twitter.stressdash.ui.filters import *  # noqa
from twitter.stressdash.persistence.store import Store

from flask import request
from jinja2 import Environment, PackageLoader


app.set_name('stressdash_%s_%s' % (getpass.getuser(), socket.gethostname()))
app.set_option('twitter_common_log_simple', True)


app.add_option(
  '-e',
  '--env',
  dest='env',
  help='Environment to run within.')

app.add_option(
  '-p',
  '--port',
  dest='port',
  default=1337,
  help='Port upon which to run.')

app.add_option(
  '--debug',
  action='store_true',
  dest='debug',
  default=False,
  help='Run in debug mode.')

app.add_option(
  '-t',
  '--twkey',
  dest='twkey',
  help='The path to the twkeys yaml file.')


def setup_metrics():
  now = time.time()
  flask_app.metrics.register(LambdaGauge('uptime', lambda: time.time() - now))

  flask_app.metrics.weekly_rps_succeeded = AtomicGauge('weekly_rps.success')
  flask_app.metrics.weekly_rps_failed = AtomicGauge('weekly_rps.failed')
  flask_app.metrics.weekly_rps_runs = AtomicGauge('weekly_rps.runs')
  flask_app.metrics.register(flask_app.metrics.weekly_rps_succeeded)
  flask_app.metrics.register(flask_app.metrics.weekly_rps_failed)
  flask_app.metrics.register(flask_app.metrics.weekly_rps_runs)

  def add_endpoint_metric(path, endpoint):
    stats = dict((k, HTTPStatusStats()) for k in (1, 2, 3, 4, 5))
    for code_prefix, observable in stats.items():
      name = 'routes.{}.{}xx'.format(endpoint, code_prefix)
      flask_app.metrics.register_observable(name, observable)
    return stats

  @flask_app.before_first_request
  def setup_endpoint_metrics():
    flask_app._endpoint_stats = {}
    for rule in flask_app.url_map.iter_rules():
      path = str(rule)
      flask_app._endpoint_stats[rule.endpoint] = add_endpoint_metric(path, rule.endpoint)

  @flask_app.before_request
  def trace_start():
    request.start_time = time.time()

  @flask_app.after_request
  def trace_end(response):
    if request.endpoint in flask_app._endpoint_stats:
      ns = 0
      if hasattr(request, 'start_time'):
        ns = int((time.time() - request.start_time) * 1e9)
      stat = flask_app._endpoint_stats[request.endpoint]
      stat[response.status_code / 100].increment(ns)
    return response


def setup_jira(twkey):
  # we use a func here so we can have a new connection
  # to jira for each jira request. the reasoning behind
  # this is that the jira authentication TTL is limited.
  def get():
    return JiraOps.from_twkey(twkey, oauth=False)
  flask_app.config['services']['get_jira'] = get


def setup_snapshot_client(twkey):
  client = SnapshotClient()
  client.set_auth(twkeys=twkey)
  flask_app.config['services']['snapshot_client'] = client


def setup_pcm_client(twkey):
  kb = KeyBird(twkey)
  creds = (kb.get_creds('username'), kb.get_creds('password'))
  def get():
    return PCM(basic_auth=creds)
  flask_app.config['services']['get_pcm'] = get


def setup_cache_client():
  cache = TwemcacheClient('twemcache_stressdash', 'smf1')
  flask_app.config['services']['cache'] = cache
  cache.start()


def setup_jinja_env():
  env = Environment(loader=PackageLoader('twitter.stressdash.ui', 'templates'))
  flask_app.config['services']['jinja_env'] = env


def initialize_resources(opts):
  if opts.debug:
    loglevel = 'google:DEBUG'
  else:
    loglevel = 'google:INFO'
  log.options.LogOptions.set_disk_log_level(loglevel)
  log.options.LogOptions.set_stderr_log_level(loglevel)
  log.logging.getLogger('requests.packages.urllib3').setLevel(log.logging.ERROR)

  config.load_env(opts.env)

  if not os.path.exists(config.DATA_DIR):
    log.info('Creating data dir: %s' % config.DATA_DIR)
    os.mkdir(config.DATA_DIR, 0700)

  Store.use_mysql(flask_app)

  flask_app.config['ELFOWL_AUTH_DOMAIN'] = config.ELFOWL_AUTH_DOMAIN
  flask_app.config['ELFOWL_ALLOWED_GROUPS'] = set(config.AUTHORIZED_GROUPS)
  flask_app.config['ELFOWL_ALLOWED_USERS'] = set(config.AUTHORIZED_USERS)
  flask_app.config['ELFOWL_HTTPS_CALLBACK'] = True
  flask_app.config['services'] = {}
  flask_app.secret_key = config.SECRET_KEY
  flask_app.metrics = RootMetrics().scope('stressdash')

  if config.ENABLE_LOGLENS:
    getLogger().addHandler(LogLensHandler(config.LOGLENS_INDICES))

  setup_metrics()
  setup_jira(opts.twkey)
  setup_snapshot_client(opts.twkey)
  setup_pcm_client(opts.twkey)
  setup_jinja_env()
  setup_cache_client()


@app.command
def server(_, opts):
  initialize_resources(opts)
  flask_app.run(
      host=config.HOST,
      port=opts.port,
      threaded=True,
  )


@app.command
def shell(_, opts):
  import IPython
  initialize_resources(opts)

  header = """Welcome to the Stressdash shell.
  flask_app: the flask app
  Store: the data store instance
  config: the Config class instance
  """

  IPython.embed(header=header, user_ns={
    'flask_app': flask_app,
    'config': config,
    'Store': Store,
  })


@app.command
def update_weekly_rps(_, opts):
  initialize_resources(opts)

  from twitter.stressdash.ui.weekly_rps import weekly_rps_run
  weekly_rps_run(opts)

app.main()
