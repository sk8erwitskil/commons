from twitter.common import log
from twitter.stressdash.ui import flask_app

from flask import Blueprint, jsonify, request


cron = Blueprint('cron', __name__, template_folder='templates')


@cron.route('/weekly_rps_callback', methods=['POST'])
def weekly_rps_callback():
  succeeded = request.form.get('succeeded', type=int)
  failed = request.form.get('failed', type=int)
  for _ in range(succeeded):
    flask_app.metrics.weekly_rps_succeeded.increment()
  for _ in range(failed):
    flask_app.metrics.weekly_rps_failed.increment()
  flask_app.metrics.weekly_rps_runs.increment()
  log.info('Logged {} succeeded, {} failed weekly rps features'.format(
      succeeded, failed))
  return jsonify(status='success')
