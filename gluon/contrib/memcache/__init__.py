from gluon.contrib.memcache.memcache import Client
from gluon.cache import CacheAbstract
import time

"""
examle of usage:

cache.memcache = MemcacheClient(request,[127.0.0.1:11211],debug=true)
"""

import cPickle as pickle
import thread
from gluon import current

DEFAULT_TIME_EXPIRE = 300 # seconds (must be the same as cache.ram)

def MemcacheClient(*a, **b):
    if not hasattr(current,'__mc_instance'):
        current.__memcache_client = MemcacheClientObj(*a, **b)
    return current.__memecache_client

class MemcacheClientObj(Client):

    meta_storage = {}
    max_time_expire = 24*3600

    def __init__(self, request, servers, debug=0, pickleProtocol=0,
                 pickler=pickle.Pickler, unpickler=pickle.Unpickler,
                 pload=None, pid=None):
        self.request=request
        if request:
            app = request.application
        else:
            app = ''
        Client.__init__(self, servers, debug, pickleProtocol,
                        pickler, unpickler, pload, pid)
        if not app in self.meta_storage:
            self.storage = self.meta_storage[app] = {
                CacheAbstract.cache_stats_name: {
                    'hit_total': 0,
                    'misses': 0,
                    }}
        else:
            self.storage = self.meta_storage[app]

    def __call__(self, key, f,
                 time_expire=DEFAULT_TIME_EXPIRE,
                 destroyer = None):
        if time_expire == None:
            time_expire = self.max_time_expire
        # this must be commented because get and set are redefined
        # key = self.__keyFormat__(key)
        now = time.time() 
        value = None
        if f is None:
            self.delete(key)
        elif time_expire==0:
            value = f()
            self.set(key, value, self.max_time_expire)
            self.set(key+':time()', now, self.max_time_expire)
        else:
            value = self.get(key)
            t0 = self.get(key+':time()')
            if value and t0:
                if (t0 < now - dt) and destroyer:
                    destroyer(value)
            else:
                value = f()
                self.set(key, value, self.max_time_expire)
                self.set(key+':time()', now, self.max_time_expire)
        return value

    def increment(self, key, value=1, time_expire=DEFAULT_TIME_EXPIRE):
        """ time_expire is ignored """
        newKey = self.__keyFormat__(key)
        obj = Client.get(self, newKey)
        if obj:
            return Client.incr(self, newKey, value)
        else:
            Client.set(self, newKey, value, self.max_time_expire)
            return value

    def set(self, key, value, time_expire=DEFAULT_TIME_EXPIRE):
        newKey = self.__keyFormat__(key)
        return Client.set(self, newKey, value, time_expire)

    def get(self, key):
        newKey = self.__keyFormat__(key)
        return Client.get(self, newKey)

    def delete(self, key):
        newKey = self.__keyFormat__(key)
        return Client.delete(self, newKey)

    def __keyFormat__(self, key):
        return '%s/%s' % (self.request.application, key.replace(' ', '_'))


