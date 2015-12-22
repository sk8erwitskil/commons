from datetime import datetime

from twitter.stressdash import config

import pytz


def localize(dt, tz):
  return pytz.timezone(tz).localize(dt)


def convert(dt, from_tz, to_tz):
  return localize(dt, from_tz).astimezone(to_tz)


def datetime_int(dt):
  return int(dt.strftime('%s'))


def adjust_time(dt, delta):
  return datetime_int(dt) + delta


def get_jira_dt(issue, field, jira):
  time_string = getattr(issue.fields, jira._fields[field])
  return datetime.strptime(time_string, config.JIRA_TIME_FMT)


def format_pcm_time(dt):
  localtime = convert_utc_pst(dt)
  local_string = localtime.strftime(config.LOCAL_TIME_FMT)
  return local_string


def convert_pcm_time(dt):
  utctime = convert_pst_utc(dt)
  return utctime.strftime(config.JIRA_TIME_FMT)


def convert_pst_utc(dt):
  return convert(dt, 'US/Pacific', pytz.utc)


def convert_utc_pst(dt):
  return convert(dt, 'UTC', pytz.timezone('US/Pacific'))
