import mimetypes

from twitter.common import log
from twitter.stressdash.persistence.store import Store
from twitter.stressdash.ui import flask_app
from twitter.stressdash.ui.auth import require_auth
from twitter.stressdash.ui.forms import (
  NewFeatureForm,
  NewTestForm,
  NewTestFromPCMForm,
)
from twitter.stressdash.ui.utils import (
  invalid_feature_id,
  render_form,
  save_feature_form,
  save_test_form,
  save_test_from_pcm_form,
  update_feature_form,
  update_test_form,
)

import pkg_resources
from flask import (
  flash,
  make_response,
  redirect,
  render_template,
  request,
  url_for,
)


# pkg_resources objects for pulling static content out of the pex
_provider = pkg_resources.get_provider('twitter.stressdash.ui')
_resource_manager = pkg_resources.ResourceManager()


@flask_app.route('/static/<path:resource>')
def static_content(resource):
  resource_path = 'static/{}'.format(resource)
  if _provider.has_resource(resource_path):
    mimetype = mimetypes.guess_type(resource)[0]
    if not mimetype:
      mimetype = 'application/octet-stream'
    return make_response(_provider.get_resource_string(_resource_manager, resource_path),
      200,
      {'Content-Type': mimetype})
  return make_response('Resource %s not found.' % resource, 404)


@flask_app.route('/', methods=['GET'])
@require_auth()
def index():
  return render_template('index.html', features=Store.all_features())


@flask_app.route('/show/feature/<int:feature_id>', methods=['GET'])
@require_auth()
def show_feature(feature_id):
  feature = Store.get_feature(feature_id)
  if feature is None:
    return invalid_feature_id(feature_id)
  return render_template('show_feature.html', feature=feature)


@flask_app.route('/show/feature/<int:feature_id>/test/<int:test_id>', methods=['GET'])
@require_auth()
def show_test(feature_id, test_id):
  feature = Store.get_feature(feature_id)
  if feature is None:
    return invalid_feature_id(feature_id)
  test = feature.get_test_by_id(test_id)
  return render_template('show_test.html', feature=feature, test=test)


@flask_app.route('/show/feature/<int:feature_id>/tests', methods=['GET'])
@require_auth()
def show_tests(feature_id):
  feature = Store.get_feature(feature_id)
  if feature is None:
    return invalid_feature_id(feature_id)
  return render_template('tests.html', feature=feature, tests=feature.tests)


@flask_app.route('/new/feature', methods=['GET', 'POST'])
@require_auth()
def new_feature():
  form = NewFeatureForm()
  if form.validate_on_submit():
    save_feature_form(form)
    return redirect(url_for('index'))
  return render_form(form, 'new_feature', 'New Feature')


@flask_app.route('/edit/feature/<int:feature_id>', methods=['GET', 'POST'])
@require_auth()
def edit_feature(feature_id):
  feature = Store.get_feature(feature_id)
  if feature is None:
    return invalid_feature_id(feature_id)
  form = NewFeatureForm(obj=feature)
  if form.validate_on_submit():
    update_feature_form(form, feature)
    return redirect(url_for('show_feature', feature_id=feature.id))
  title = 'Edit "{}"'.format(feature.name)
  return render_form(form, 'edit_feature', title, {'feature_id': feature.id})


@flask_app.route('/delete/feature', methods=['POST'])
@require_auth()
def delete_feature():
  feature_id = request.form.get('feature_id')
  feature = Store.get_feature(feature_id)
  if feature is None:
    return invalid_feature_id(feature_id)
  Store.delete_feature(feature)
  if feature.exc:
    flash('Error deleting feature: {}'.format(feature.exc), 'danger')
  else:
    flash('Deleted feature: {}'.format(feature.name), 'success')
  return redirect(url_for('index'))


@flask_app.route('/new/feature/<int:feature_id>/test', methods=['GET', 'POST'])
@require_auth()
def new_test(feature_id):
  feature = Store.get_feature(feature_id)
  if feature is None:
    return invalid_feature_id(feature_id)
  form = NewTestForm()
  form.feature_id.data = feature_id
  if form.validate_on_submit():
    if save_test_form(form, feature):
      return redirect(url_for('show_tests', feature_id=feature_id))
  title = 'New "{}" Test'.format(feature.name)
  return render_form(form, 'new_test', title, {'feature_id': feature.id})


@flask_app.route('/edit/feature/<int:feature_id>/test/<int:test_id>', methods=['GET', 'POST'])
@require_auth()
def edit_test(feature_id, test_id):
  feature = Store.get_feature(feature_id)
  if feature is None:
    return invalid_feature_id(feature_id)
  test = feature.get_test_by_id(test_id)
  form = NewTestForm(obj=test)
  if form.validate_on_submit():
    if update_test_form(form, feature, test):
      return redirect(url_for('show_test', feature_id=feature_id, test_id=test.id))
  title = 'Edit "{}" Test'.format(feature.name)
  return render_form(form, 'edit_test', title, {'feature_id': feature_id, 'test_id': test_id})


@flask_app.route('/delete/feature/test', methods=['POST'])
@require_auth()
def delete_test():
  test_id = request.form.get('test_id', type=int)
  log.info('Deleting test with id {}'.format(test_id))
  test = Store.get_test(test_id)
  feature_id = test.feature_id
  Store.delete_test(test)
  if test.exc:
    flash('Error deleting test: {}'.format(test.exc), 'danger')
  else:
    flash('Deleted test: {}'.format(test), 'success')
  return redirect(url_for('show_tests', feature_id=feature_id))


@flask_app.route('/recent', methods=['GET'])
@require_auth()
def recent(days=14):
  num_days = int(request.args.get('days', days))
  recent_tests = sorted(Store.get_recent_tests(num_days), key=lambda x: x.ended_at)
  return render_template('recent_tests.html',
                         tests=sorted(recent_tests, key=lambda x: x.ended_at)[::-1],
                         days=num_days,
                         get_feature=Store.get_feature)


@flask_app.route('/pcm_import/feature/<int:feature_id>', methods=['GET', 'POST'])
@require_auth()
def new_test_from_pcm(feature_id):
  feature = Store.get_feature(feature_id)
  if feature is None:
    return invalid_feature_id(feature_id)
  form = NewTestFromPCMForm()
  if form.validate_on_submit():
    if save_test_from_pcm_form(form, feature):
      return redirect(url_for('show_tests', feature_id=feature.id))
  title = 'New "{}" Test from PCM'.format(feature.name)
  return render_form(form, 'new_test_from_pcm', title, {'feature_id': feature.id})


@flask_app.route('/quitquitquit', methods=['GET', 'POST'])
@flask_app.route('/abortabortabort', methods=['GET', 'POST'])
def shutdown():
  func = request.environ.get('werkzeug.server.shutdown')
  if func is None:
    raise RuntimeError('Not running with the Werkzeug Server')
  flask_app.config['services']['cache'].stop()
  func()
