import sys
from typing import override
from lru import LRU
from KnowledgeGraph import Graph, SPARQLKG
def evicted(key, value):
  print("removing: %s, %s" % (key, value))

class HybridKG(Graph):
    def __init__(self, url, prefix: str, multiprocess: bool, workers: int):
        self._prefix = prefix
        self._sparql = SPARQLKG(url, prefix, multiprocess, workers)
        self._adj_cache = LRU(35_000, callback=evicted)
        self._type_cache = LRU(35_000, callback=evicted)

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop('_adj_cache', None)
        state.pop('_type_cache', None)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._adj_cache = LRU(35_000, callback=evicted)
        self._type_cache = LRU(35_000, callback=evicted)

    def freeze(self, multiprocess: bool, workers: int):
        self._sparql.freeze(multiprocess=multiprocess, workers=workers)

    def clean_uri(self, uri) -> str:
        return self._sparql.clean_uri(uri)

    def resolve_to_uri(self, node):
        return self._sparql.resolve_to_uri(node)

    def get_all_predicates(self):
        return self._sparql.get_all_predicates()

    def get_balanced_predicate_batches(self):
        return self._sparql.get_balanced_predicate_batches()

    def get_triples(self, subject=None, predicate=None, object=None):
        # No caching because cache hit is unlikely
        return self._sparql.get_triples(subject, predicate, object)

    def get_type(self, subject, type_predicate):
        cache = self._type_cache.get(subject, None)
        if not (cache is None):
            return cache
        result = self._sparql.get_type(subject, type_predicate)
        self._type_cache[subject] = result
        return result

    def get_adjacent_triples(self, node):
        node = sys.intern(node)
        cache = self._adj_cache.get(node, None)
        if not (cache is None):
            return cache
        result = self._sparql.get_adjacent_triples(node)
        self._adj_cache[node] = result
        return result

    def get_edges(self, predicate):
        return self._sparql.get_edges(predicate)

    @override
    def patterns_in_graph(self, body: set[tuple], name_dict: dict) -> bool:
        return self._sparql.patterns_in_graph(body, name_dict)

    def get_negative_edges(self, predicate):
        return self._sparql.get_negative_edges(predicate)

    def is_literal(self, object):
        return self._sparql.is_literal(object)

    def is_valid_comp(self, node):
        return self._sparql.is_valid_comp(node)

    def literal_type(self, node):
        return self._sparql.literal_type(node)

    def is_literal_comp(self, predicate):
        return self._sparql.is_literal_comp(predicate)

    def add_negative_triples(self, triples):
        return self._sparql.add_negative_triples(triples)