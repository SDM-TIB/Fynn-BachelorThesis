from collections import defaultdict
from KnowledgeGraph import Graph, SPARQLKG

class HybridKG(Graph):
    def __init__(self, url, prefix: str):
        self._prefix = prefix
        self._sparql = SPARQLKG(url)
        self._adjacent = defaultdict(set[tuple[str, str]])
        self._types = defaultdict(set)

    def clean_uri(self, uri):
        return self._sparql.clean_uri(uri)

    def resolve_to_uri(self, node):
        return node

    def get_all_subjects(self):
        return self._sparql.get_all_subjects()

    def get_all_predicates(self):
        return self._sparql.get_all_predicates()

    def get_all_objects(self):
        return self._sparql.get_all_objects()

    def get_triples(self, subject=None, predicate=None, object=None):
        # No caching because cache hit is unlikely
        return self._sparql.get_triples(subject, predicate, object)

    def get_type(self, subject, type_predicate):
        cached = self._types[subject]
        if cached:
            return cached
        result = self._sparql.get_type(subject, type_predicate)
        self._types[subject] = result
        return result

    def get_adjacent_triples(self, node):
        cached = self._adjacent.get(node)
        if cached:
            return cached
        result = self._sparql.get_adjacent_triples(node)
        self._adjacent[node] = result
        return result

    def get_edges(self, predicate):
        return self._sparql.get_edges(predicate)

    def get_objects(self, predicate):
        return self._sparql.get_objects(predicate)

    def get_predicates(self, subject):
        return self._sparql.get_predicates(subject)

    def get_negative_edges(self, predicate):
        return self._sparql.get_negative_edges(predicate)

    def is_literal(self, object):
        return self._sparql.is_literal(object)

    def is_valid_comp(self, node):
        return self._sparql.is_valid_comp(node)

    def literal_type(self):
        return self._sparql.literal_type()

    def is_literal_comp(self):
        return self._sparql.is_literal_comp()

    def add_negative_triples(self, triples):
        return self._sparql.add_negative_triples(triples)