from datetime import datetime

from flask_wtf import Form
from wtforms import (
  BooleanField,
  DateTimeField,
  HiddenField,
  IntegerField,
  StringField,
  TextField,
  validators,
)
from wtforms.widgets import HTMLString, html_params
# checkstyle: noqa


class DateTimePicker(object):
  data_template = (
    '<div class="input-group date" id="datepicker_{}">'
    '<input type="text" class="form-control" {} />'
    '<span class="input-group-addon">'
    '<span class="glyphicon glyphicon-calendar">'
    '</span>'
    '</div>'
  )

  def __call__(self, field, **kwargs):
    kwargs.setdefault('id', field.id)
    kwargs.setdefault('name', field.name)
    if not field.data:
      field.data = ""
    params = html_params(value=field.data, **kwargs)
    return HTMLString(self.data_template.format(field.id, params))


class NewFeatureForm(Form):
  id = HiddenField('Id', [validators.Optional()])
  name = StringField('Name', [validators.Required()])
  corvus_name = StringField('Corvus Alias', [validators.Required()])
  weekly_max_rps = IntegerField('Last week\'s max RPS', [validators.Optional()])
  yearly_max_rps = IntegerField('Max RPS for {}'.format(datetime.utcnow().year - 1), [validators.Optional()])
  max_tested_rps = IntegerField('Historical testing max RPS', [validators.Optional()])
  target_rps = IntegerField('Target RPS', [validators.Optional()])
  highest_recorded_rps = IntegerField('Highest recorded RPS', [validators.Optional()])
  dashboard_slugs = StringField('Viz Dashboard Slugs',
    description='Comma-separated list of viz dashboard slugs',
    validators=[validators.Optional()])
  rps_query = StringField('RPS Cuckoo Query', [validators.Optional()])


class NewTestForm(Form):
  id = HiddenField('Id', [validators.Optional()])
  feature_id = HiddenField('Feature ID', [validators.Optional()])
  started_at = DateTimeField('Test start time', [validators.Required()], widget=DateTimePicker())
  ended_at = DateTimeField('Test end time', [validators.Required()], widget=DateTimePicker())
  zone = StringField('Zone', [validators.Required()])
  sustained_minutes = IntegerField('Sustained number of minutes', [validators.Optional()])
  jira_key = StringField('Jira Ticket', [validators.Optional()])
  target_rps = IntegerField('Target RPS',
    description='If blank, defaults to the target rps set in the parent feature.',
    validators=[validators.Optional()])
  max_rps = IntegerField('Max RPS reached',
    description='If blank, will query cuckoo for the max rps during the test.',
    validators=[validators.Optional()])
  comment = TextField('Comment', [validators.Optional()])
  successful = BooleanField('Test was successful')


class NewTestFromPCMForm(Form):
  pcm_key = StringField('PCM Ticket Key', [validators.Required()])
