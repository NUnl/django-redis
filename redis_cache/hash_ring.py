# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import bisect
import hashlib

import logging
logger = logging.getLogger(__name__)

class HashRing(object):
    nodes = []

    def __init__(self, nodes=[], replicas=128):
        self.replicas = replicas
        self.ring = {}
        self.sorted_keys = []

        for node in nodes:
            self.add_node(node)

    def add_node(self, node):
        self.nodes.append(node)

        for x in range(self.replicas):
            _key = "{0}:{1}".format(node, x)
            _hash = hashlib.sha256(_key.encode('utf-8')).hexdigest()

            self.ring[_hash] = node
            self.sorted_keys.append(_hash)

        self.sorted_keys.sort()

    def remove_node(self, node):
        self.nodes.remove(node)
        for x in range(self.replicas):
            _hash = hashlib.sha256("%s:%d" % (node, x)).hexdigest()
            self.ring.remove(_hash)
            self.sorted_keys.remove(_hash)

    def get_node(self, key):
        n, i = self.get_node_pos(key)
        return n

    def get_node_pos(self, key):
        if len(self.ring) == 0:
            return (None, None)

        _hash = hashlib.sha256(key.encode('utf-8')).hexdigest()
        idx = bisect.bisect(self.sorted_keys, _hash)
        idx = min(idx, (self.replicas * len(self.nodes))-1)
        
        # this is NOT a proper fix for issue #48. It suppresses IndexError (occuring
        # having 2 shards and an idx of 256) by returning (None, None) which is a valid response
        try:
            return (self.ring[self.sorted_keys[idx]], idx)
        except IndexError:
            logger.warning('Suppressed IndexError when fetching idx {0} from self.sorted_keys with length {1}'.format(
                idx, len(self.sorted_keys)), exc_info=True)
            return (None, None)

    def iter_nodes(self, key):
        if len(self.ring) == 0: yield None, None
        node, pos = self.get_node_pos(key)
        for k in self.sorted_keys[pos:]:
            yield k, self.ring[k]

    def __call__(self, key):
        return self.get_node(key)
