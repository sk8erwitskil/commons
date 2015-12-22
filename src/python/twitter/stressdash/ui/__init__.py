# checkstyle: noqa
from twitter.common import app
from twitter.common_internal.auth.elfowl.flask_elfowl import ElfOwlHandler
from twitter.common_internal.flask import CommonHttp, ServerType
from twitter.stressdash import config

from flask import Flask
from jinja2 import PackageLoader

# enable tracing
app.set_option('twitter_common_app_modules_varz_trace_endpoints', True)
app.set_option('twitter_common_app_modules_varz_trace_namespace', 'http')


flask_app = Flask(__name__, static_url_path='')
CommonHttp.init_app(flask_app, server_type=ServerType.THREADED)
flask_app.jinja_env.loader = PackageLoader('twitter.stressdash.ui')
elfowl = ElfOwlHandler(flask_app)

# Import the views for the web UI after the app has been created
import twitter.stressdash.ui.views

from twitter.stressdash.ui.api import api
flask_app.register_blueprint(api, url_prefix='/api/{}'.format(config.API_VER))

from twitter.stressdash.ui.cron import cron
flask_app.register_blueprint(cron, url_prefix='/cron')
