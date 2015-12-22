from twitter.stressdash.ui import flask_app

from flask import request


@flask_app.context_processor
def inject_current_user():
  return dict(current_user=request.elfowl_cookie.user)


@flask_app.context_processor
def inject_oi_key():
  key = '{}_oi_disabled'.format(request.elfowl_cookie.user)
  return dict(oi_key=key)


@flask_app.context_processor
def inject_oi_disabled():
  key = '{}_oi_disabled'.format(request.elfowl_cookie.user)
  cache = flask_app.config['services']['cache']
  disabled = bool(cache.get(key))
  return dict(oi_disabled=disabled)
