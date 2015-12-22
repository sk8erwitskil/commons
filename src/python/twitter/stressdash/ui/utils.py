from twitter.common import log
from twitter.ops.jira import JiraOps
from twitter.stressdash import config
from twitter.stressdash.ui import flask_app
from twitter.stressdash.ui.metrics_util import get_metrics
from twitter.stressdash.ui.time_util import (
  convert_pst_utc,
  format_pcm_time,
  get_jira_dt,
)
from twitter.stressdash.persistence.store import Store

import yaml
from flask import flash, redirect, render_template, url_for


def render_form(form, submit_url, form_title, kwargs={}):
  return render_template('forms.html',
      form=form,
      submit_url=submit_url,
      form_title=form_title,
      kwargs=kwargs)


def invalid_feature_id(feature_id):
  flash('{} is not a valid feature id'.format(feature_id), 'danger')
  return redirect(url_for('index'))


def feature_save_flash(feature):
  if feature.exc:
    flash('Error saving feature: {}'.format(feature.exc), 'danger')
  else:
    flash('Saved feature: {}'.format(feature.name), 'success')


def test_save_flash(feature, test):
  if test.exc:
    flash('Error saving test: {}'.format(test.exc), 'danger')
  else:
    flash('Saved test for feature "{}"'.format(feature.name), 'success')


def save_feature_form(form):
  feature = Store.new_feature(
    name=form.name.data,
    corvus_name=form.corvus_name.data,
    weekly_max_rps=form.weekly_max_rps.data,
    yearly_max_rps=form.yearly_max_rps.data,
    max_tested_rps=form.max_tested_rps.data,
    target_rps=form.target_rps.data,
    highest_recorded_rps=form.highest_recorded_rps.data,
    dashboard_slugs=form.dashboard_slugs.data,
    rps_query=form.rps_query.data,
  )
  feature_save_flash(feature)


def update_feature_form(form, feature):
  feature.name = form.name.data
  feature.corvus_name = form.corvus_name.data
  feature.weekly_max_rps = form.weekly_max_rps.data
  feature.yearly_max_rps = form.yearly_max_rps.data
  feature.max_tested_rps = form.max_tested_rps.data
  feature.target_rps = form.target_rps.data
  feature.highest_recorded_rps = form.highest_recorded_rps.data
  feature.dashboard_slugs = form.dashboard_slugs.data
  feature.rps_query = form.rps_query.data
  Store.save_feature(feature)
  feature_save_flash(feature)


def get_max_rps(feature, max_rps, zone, start, end):
  # if the feature does not specify an rps_query
  # or the user manually entered in a max_rps
  if not feature.rps_query or max_rps:
    return max_rps
  log.info('No max_rps specified. Calculating...')
  metrics = get_metrics(
    feature.rps_query,
    zone,
    start,
    end)
  return max(metrics)


def get_target_rps(feature, target_rps):
  # if the user overrides then use that otherwise
  # pull target_rps from feature object
  return target_rps or feature.target_rps


def update_test_form(form, feature, test):
  test.zone = form.zone.data
  test.started_at = form.started_at.data
  test.ended_at = form.ended_at.data
  test.target_rps = get_target_rps(feature, form.target_rps.data)
  test.max_rps = get_max_rps(
    feature,
    form.max_rps.data,
    form.zone.data,
    convert_pst_utc(form.started_at.data),
    convert_pst_utc(form.ended_at.data))
  test.sustained_minutes = form.sustained_minutes.data
  test.jira_key = form.jira_key.data
  test.successful = form.successful.data
  test.comment = form.comment.data
  ret = Store.save_test(test)
  test_save_flash(feature, test)
  return ret


def save_test_form(form, feature):
  max_rps = get_max_rps(
    feature,
    form.max_rps.data,
    form.zone.data,
    convert_pst_utc(form.started_at.data),
    convert_pst_utc(form.ended_at.data))
  test = Store.new_test(
    feature,
    zone=form.zone.data,
    started_at=form.started_at.data,
    ended_at=form.ended_at.data,
    target_rps=get_target_rps(feature, form.target_rps.data),
    max_rps=max_rps,
    sustained_minutes=form.sustained_minutes.data,
    jira_key=form.jira_key.data,
    successful=form.successful.data,
    comment=form.comment.data
  )
  test_save_flash(feature, test)
  return test.exc is None


def save_test_from_pcm_form(form, feature):
  log.info('Creating new test from {}'.format(form.pcm_key.data))
  jira = flask_app.config['services']['get_jira']()

  try:
    issue = jira.get_issue(form.pcm_key.data)
  except JiraOps.JiraOpsException as e:
    flash('Error fetching {}. {}'.format(form.pcm_key.data, e), 'danger')
    return False

  data = get_tag_data(issue)
  if not data:
    log.error('Unable to parse tags in {}'.format(issue.key))
    return False

  start = get_jira_dt(issue, 'actual_start', jira)
  end = get_jira_dt(issue, 'actual_completion', jira)

  test = Store.new_test(
    feature,
    started_at=format_pcm_time(start),
    ended_at=format_pcm_time(end),
    jira_key=issue.key,
    target_rps=get_target_rps(feature, data.get('target_rps')),
    max_rps=get_max_rps(feature, data.get('max_rps'), data['zone'], start, end),
    **data
  )
  test_save_flash(feature, test)
  return True


def get_tag_data(ticket):
  """
  Extracts tag contents from a ticket. Expects this format:

    <<stresstest_stats>>
    zone: smf1
    max_rps: 123
    target_rps: 1233
    sustained_minutes: 5
    successful: true
    comment: woohoo!
    <<stresstest_stats>>
  """

  value = config.JIRA_DESC_REGEX.search(ticket.fields.description)
  if not value:
    flash('<<stresstest_stats>> tag not found', 'danger')
    return None
  try:
    data = yaml.load(value.group('text'))
    for tag in ['zone', 'sustained_minutes']:
      if not data.get(tag):
        flash('{}: missing "{}" field'.format(ticket.key, tag), 'danger')
        return None
    return data
  except (ValueError, yaml.scanner.ScannerError) as e:
    flash('Error deserializing {}: {}'.format(ticket.key, e), 'danger')
    return None
