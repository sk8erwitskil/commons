from datetime import datetime

from twitter.common import log
from twitter.common.concurrent import as_completed, ThreadPoolExecutor
from twitter.stressdash import config
from twitter.stressdash.persistence.store import Store
from twitter.stressdash.ui import flask_app
from twitter.stressdash.ui.auth import require_auth
from twitter.stressdash.ui.pcm_util import create_pcm
from twitter.stressdash.ui.snapshot_util import (
  create_viz_snapshot,
  delete_viz_snapshot,
)

from flask import Blueprint, flash, jsonify, redirect, request


api = Blueprint('api', __name__, template_folder='templates')


def json_or_redirect(error=None, next_url=None):
  if error:
    log.error(error)
    flash('Error: {}'.format(error), 'danger')
  if next_url:
    return redirect(next_url)
  return jsonify(error=error)


def curyear_label():
  year = int(datetime.utcnow().strftime('%y')) + 1
  return '(NYE{}_PREP)'.format(year)


@api.route('/cache_set', methods=['POST'])
def cache_set():
  key = request.form.get('key')
  value = request.form.get('value')
  ttl = request.form.get('ttl', config.DEFAULT_CACHE_TTL, type=int)
  cache = flask_app.config['services']['cache']
  cache.set(key, value, expire=ttl)
  log.info('Set cache {}={} ttl={}'.format(key, value, ttl))
  return jsonify(key=value, ttl=ttl)


@api.route('/cache_get', methods=['GET'])
def cache_get():
  key = request.form.get('key')
  cache = flask_app.config['services']['cache']
  return jsonify(key=cache.get(key))


@api.route('/running_tests', methods=['GET'])
@require_auth()
def current_tests():
  cache = flask_app.config['services']['cache']
  results = cache.get('running_tests')
  if results is None:
    jira = flask_app.config['services']['get_jira']()
    status = '({})'.format(','.join(config.PCM_STATUSES))
    running = jira.search_issues(
      not_in={'status': status},
      is_in={'labels': config.PCM_LABELS, 'component': config.PCM_COMPONENT})
    results = [{'key': i.key, 'summary': i.fields.summary} for i in running]
    cache.set('running_tests', results, expire=config.RUNNING_TESTS_TTL)
  return jsonify(results=results)


@api.route('/outstanding_issues', methods=['GET'])
def outstanding_issues():
  cache = flask_app.config['services']['cache']
  results = cache.get('outstanding_issues')
  if results is None:
    jira = flask_app.config['services']['get_jira']()
    running = jira.search_issues(
      is_in={'labels': curyear_label(), 'status': '("open")'})
    results = [{'key': i.key, 'summary': i.fields.summary} for i in running]
    cache.set('outstanding_issues', results, expire=config.RUNNING_TESTS_TTL)
  return jsonify(results=results)


@api.route('/create_snapshot', methods=['POST'])
@require_auth()
def create_snapshot():
  test_id = request.form.get('test_id', type=int)
  slug = request.form.get('slug')
  next_url = request.form.get('next')

  if not slug:
    error = 'Must specify slug argument'
    return json_or_redirect(error, next_url)

  error = snapshot_from_slug(slug, test_id)
  if error is not None:
    return json_or_redirect(error, next_url)
  flash('Created new snapshot for {}'.format(slug), 'success')
  return json_or_redirect(None, next_url)


@api.route('/delete_snapshot', methods=['POST'])
@require_auth()
def delete_snapshot():
  client = flask_app.config['services']['snapshot_client']
  test_id = request.form.get('test_id', type=int)
  snapshot_id = request.form.get('snapshot_id', type=int)
  next_url = request.form.get('next')
  test = Store.get_test(test_id)
  for snapshot in test.snapshots:
    if snapshot.snapshot_id == snapshot_id:
      slug = snapshot.slug
      status = delete_viz_snapshot(client, test, slug)
      if status is None:
        flash('Deleted snapshot {} for this test'.format(slug),
            'success')
        return json_or_redirect(None, next_url)
      return json_or_redirect(str(status), next_url)
  error = 'No snapshot with id {}'.format(snapshot_id)
  return json_or_redirect(error, next_url)


@api.route('/create_dependency_snapshots', methods=['POST'])
@require_auth()
def create_dependency_snapshots():
  test_id = request.form.get('test_id', type=int)
  next_url = request.form.get('next')
  test = Store.get_test(test_id)
  feature = Store.get_feature(test.feature_id)
  slugs = [s.strip() for s in feature.dashboard_slugs.split(',')]
  with ThreadPoolExecutor(max_workers=len(slugs)) as ex:
    err_futures = [ex.submit(snapshot_from_slug, slug, test_id) for slug in slugs]
    for res in as_completed(err_futures):
      error = res.exception() or res.result()
      if error is not None:
        return json_or_redirect(str(error), next_url)
  flash('Created new snapshots for {}'.format(slugs), 'success')
  return json_or_redirect(None, next_url)


def snapshot_from_slug(slug, test_id):
  client = flask_app.config['services']['snapshot_client']
  test = Store.get_test(test_id)
  delete_viz_snapshot(client, test, slug)
  try:
    snapshot = create_viz_snapshot(client, test, slug)
    if snapshot.exc:
      log.error('Got an error creating {}'.format(slug))
      return str(snapshot.exc)
  except client.ClientError as e:
    error = 'Unable to create snapshot for slug {}: '.format(slug)
    return error + str(e)


@api.route('/create_pcm', methods=['POST'])
@require_auth()
def create_pcm_for_feature():
  zone = request.form.get('zone')
  qps_per_batch = request.form.get('qps_per_batch', type=int)
  feature_id = request.form.get('feature_id', type=int)
  start_time = request.form.get('start_time')
  next_url = request.form.get('next')
  feature = Store.get_feature(feature_id)
  res = create_pcm(feature, zone, qps_per_batch, start_time)
  return json_or_redirect(res, next_url)
