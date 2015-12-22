import getpass

from functools import wraps

from twitter.stressdash import config
from twitter.stressdash.ui import elfowl

from flask import request


class DummyElfOwlCookie(object):
  @property
  def groups(self):
    return ['sre-group']

  @property
  def user(self):
    return getpass.getuser()

  @property
  def timestamp(self):
    return 0


def require_auth(allowed_groups=config.AUTHORIZED_GROUPS,
    allowed_users=config.AUTHORIZED_USERS):
  """
  Decorator that requires Elf Owl authentication on a route if auth is enabled.

  allowed_groups -- set of groups the user has to be a member of
  allowed_users -- set of users that the user has to be a member of
  """

  def wrapper(view_func):
    @wraps(view_func)
    def optionally_authenticate(*args, **kw):
      @elfowl.require(allowed_groups=set(allowed_groups),
          allowed_users=set(allowed_users))
      def _auth_decorated(*args, **kw):
        return view_func(*args, **kw)

      if config.ENABLE_AUTHENTICATION:
        # Authentication is enabled, so calls the ElfOwl auth-decorated method.
        return _auth_decorated(*args, **kw)
      else:
        # Authentication is disabled, so returns a mock ElfOwl cookie and calls
        # the decorated method directly.
        request.elfowl_cookie = DummyElfOwlCookie()
        return view_func(*args, **kw)
    return optionally_authenticate
  return wrapper
