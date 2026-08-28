from diskcache import Cache
from KnowledgeGraph import Graph, SPARQLKG

class HybridKG(Graph):
    def __init__(self, url, prefix: str):
        self._prefix = prefix
        self._sparql = SPARQLKG(url)
        self._cache = Cache(cache_dir="./kg_cache")

    def freeze(self, multiprocess: bool, workers: int):
        self._sparql.freeze(multiprocess=multiprocess, workers=workers)

    def clean_uri(self, uri) -> str:
        return self._sparql.clean_uri(uri)

    def resolve_to_uri(self, node):
        return node

    def get_all_predicates(self):
        return self._sparql.get_all_predicates()

    def get_balanced_predicate_batches(self):
        return self._sparql.get_balanced_predicate_batches()

    def get_triples(self, subject=None, predicate=None, object=None):
        # No caching because cache hit is unlikely
        return self._sparql.get_triples(subject, predicate, object)

    def get_type(self, subject, type_predicate):
        cache_key = f"t:{self.clean_uri(subject)}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached
        result = self._sparql.get_type(subject, type_predicate)
        self._cache.set(cache_key, result)
        return result

    def get_adjacent_triples(self, node):
        cache_key = f"ad:{self.clean_uri(node)}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached
        result = self._sparql.get_adjacent_triples(node)
        self._cache.set(cache_key, result)
        return result

    def get_edges(self, predicate):
        return self._sparql.get_edges(predicate)

    def get_negative_edges(self, predicate):
        return self._sparql.get_negative_edges(predicate)

    def is_literal(self, object):
        return self._sparql.is_literal(object)

    def is_valid_comp(self, node):
        return self._sparql.is_valid_comp(node)

    def literal_type(self, node):
        return self._sparql.literal_type(node)

    def is_literal_comp(self):
        return self._sparql.is_literal_comp()

    def add_negative_triples(self, triples):
        return self._sparql.add_negative_triples(triples)