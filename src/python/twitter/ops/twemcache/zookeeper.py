from time import sleep

from twitter.common import log
from twitter.common.concurrent import ThreadPoolExecutor
from twitter.common_internal.zookeeper.tunneler import TunneledZookeeper
from twitter.common_internal.zookeeper.twitter_serverset_kazoo import KazooTwitterServerSet

from kazoo.retry import KazooRetry


class TwemcacheZK(object):

  CACHE_ROLE = 'cache'
  RETRIES = 3
  ZK_CLUSTER = 'sdzookeeper.{}.twitter.com'
  ZK_HEALTH_INTERVAL = 5

  def __init__(self, twname, zone, memcached, prod=False):
    self._zk_cluster = self.ZK_CLUSTER.format(zone)
    self._twname = twname
    self._env = 'prod' if prod else 'test'
    self._memcached = memcached
    self._reset()

  def _reset(self):
    log.info('Resetting hosts')
    self._memcached.expire_all()

  def _on_join(self, instance):
    host = instance.service_endpoint.host
    port = int(instance.service_endpoint.port)
    combo = '{}:{}'.format(host, port)
    if combo not in self._memcached.clients:
      log.info('Found new twemcache host: {}'.format(combo))
      self._memcached.add_server(host, port)

  def _on_leave(self, instance):
    host = instance.service_endpoint.host
    port = int(instance.service_endpoint.port)
    combo = '{}:{}'.format(host, port)
    if combo in self._memcached.clients:
      log.info('Twemcache host has left: {}'.format(combo))
      self._memcached.expire_server(host, port)

  def _stop_zk(self):
    log.info('Removing current zk connections')
    self._zk.stop()
    self._zk.close()

  def _stop_watcher(self):
    self._die = True
    log.info('Waiting for zk watcher to terminate')
    self._ex.shutdown()

  def _watch_zk(self):
    log.info('Starting zk watcher')
    while True:
      if self._die is True:
        log.info('Killing zk watcher')
        break
      log.debug('Checking zk health')
      if not self._zk.connected:
        # remove all hosts since we cannot be certain
        # what the hosts are
        self._reset()
        self._wait_for_zk()
        self.update()
      sleep(self.ZK_HEALTH_INTERVAL)

  def _zk_retry(self):
    return KazooRetry(max_tries=self.RETRIES, backoff=1)

  def connect(self):
    log.info('Connecting to zookeeper')
    self._zk = TunneledZookeeper.get_kazoo(
      self._zk_cluster,
      connection_retry=self._zk_retry(),
      command_retry=self._zk_retry())
    self._wait_for_zk()

    # setup the watcher thread to make sure hosts stay updated
    self._die = False
    self._ex = ThreadPoolExecutor(max_workers=1)
    self._zk_watcher_thread = self._ex.submit(self._watch_zk)

  def _wait_for_zk(self):
    log.info('Waiting for ZK')
    while self._zk.connected is False:
      sleep(1)
    log.info('ZK Connected!')

  def update(self):
    self._reset()
    hosts = KazooTwitterServerSet(
      self.CACHE_ROLE,
      self._env,
      self._twname,
      zk=self._zk,
      on_join=self._on_join,
      on_leave=self._on_leave)
    combos = [str(h.service_endpoint) for h in hosts]
    log.debug('Found hosts: {}'.format(combos))
    return combos

  def close(self):
    self._stop_watcher()
    self._stop_zk()
    return True
