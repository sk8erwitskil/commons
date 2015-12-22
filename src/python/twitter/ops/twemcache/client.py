import json

from twitter.common import log
from twitter.ops.twemcache.zookeeper import TwemcacheZK

from pymemcache.client.hash import HashClient


def json_serializer(key, value):
  if type(value) == str:
    return value, 1
  return json.dumps(value), 2


def json_deserializer(key, value, flags):
  if flags == 1:
    return value
  if flags == 2:
    return json.loads(value)


class TwemcacheClient(HashClient):
  """
  Client to interact with twemcache.

  This client subclasses pymemcached so any method
  available in that library is available here as well.

  Example:
    from twitter.ops.twemcache.client import TwemcacheClient
    cache = TwemcacheClient('twemcache_stressdash', 'smf1')
    cache.set('key', 'value', expire=60)
    cache.get('key')

  Args:
    twemcache_name(str): the name of the twemcache service cluster
    zone(str): the cluster. i.e. smf1 or atla
    prod(bool): if the twemcache service is in the prod cluster
  """

  def __init__(self, twemcache_name, zone, prod=False):
    super(TwemcacheClient, self).__init__(
      [],
      serializer=json_serializer,
      deserializer=json_deserializer,
      timeout=5,
      connect_timeout=5,
      retry_attempts=1,
      no_delay=True,
    )
    self._twzk = TwemcacheZK(twemcache_name, zone, self, prod)
    log.info('Created twemcache client')

  def expire_server(self, host, port):
    key = '{}:{}'.format(host, port)
    combo = (host, port)
    if key in self.clients:
      self.clients.pop(key)
    if combo in self._failed_clients:
      self._failed_clients.pop(combo)
    if combo in self._dead_clients:
      self._dead_clients.pop(combo)
    self.hasher.remove_node(key)

  def expire_all(self):
    for _, client in self.clients.items():
      client.close()
      self.expire_server(*client.server)

  @property
  def hosts(self):
    return self.clients.keys()

  def stop(self):
    self.expire_all()
    return self._twzk.close()

  def start(self):
    self._twzk.connect()
    self._twzk.update()
