from collections import defaultdict
from rdflib.plugins.stores.sparqlstore import SPARQLStore
from rdflib import Graph, Literal, URIRef, Node
from KnowledgeGraph.Graph import Graph as KG

class SPARQLKG(KG):

    def __init__(self, url):
        self._store = SPARQLStore(query_endpoint=url)
        self._graph = Graph(store=self._store)
        self._negative_triples: set[tuple[str, str, str]] = set()
        self._negative_pred = defaultdict(set)

    def _select(self, query: str) -> list:
        return list(self._graph.query(query))

    def _to_node(self, val):
        """Converts raw strings to RDFLib terms if needed."""
        if val is None or isinstance(val, Node):
            return val
        if isinstance(val, str):
            # If it looks like a URL, wrap in URIRef; otherwise treat as Literal
            if val.startswith("http://") or val.startswith("https://") or val.startswith("urn:"):
                return URIRef(val)
            return Literal(val)
        return val

    def resolve_to_uri(self, node):
        #TODO: Implement
        return node

    # region All
    def get_all_subjects(self):
        query = "SELECT DISTINCT ?s WHERE { ?s ?p ?o }"
        return {row[0] for row in self._select(query)}

    def get_all_predicates(self):
        query = "SELECT DISTINCT ?p WHERE { ?s ?p ?o }"
        return {row[0] for row in self._select(query)}

    def get_all_objects(self):
        query = "SELECT DISTINCT ?o WHERE { ?s ?p ?o }"
        return {row[0] for row in self._select(query)}

    def get_all_negative_triples(self):
        pass
    #endregion

    # region Specific
    #TODO: Check input data types
    def get_triples(self, subject = None, predicate = None, object = None):
        s_node = self._to_node(subject)
        p_node = self._to_node(predicate)
        o_node = self._to_node(object)
        return set(self._graph.triples((s_node, p_node, o_node)))

    def get_adjacent_triples(self, node):
        query = f"""
        SELECT DISTINCT ?s ?p ?o WHERE {{
            {{ <{node}> ?p ?o . BIND(<{node}> AS ?s) }}
            UNION
            {{ ?s ?p <{node}> . BIND(<{node}> AS ?o) }}
        }}
        """
        return self._select(query)

    def get_edges(self, predicate):
        query = f"SELECT DISTINCT ?s ?o WHERE {{ ?s <{predicate}> ?o }}"
        return {(row[0], row[1]) for row in self._select(query)}

    def get_objects(self, predicate):
        query = f"SELECT DISTINCT ?o WHERE {{ ?s <{predicate}> ?o }}"
        return {row[0] for row in self._select(query)}

    def get_predicates(self, subject):
        query = f"SELECT DISTINCT ?p WHERE {{ <{subject}> ?p ?o }}"
        return {row[0] for row in self._select(query)}

    def get_negative_edges(self, predicate):
        return self._negative_pred.get(predicate, set())
    #endregion

    # region Literals
    def is_literal(self, object):
        return isinstance(object, Literal)

    def is_valid_comp(self, node):
        pass

    def literal_type(self, ):
        pass

    def is_literal_comp(p):
        pass
    # endregion

    # Modification
    def remove_triples(self, triples):
        pass

    def add_negative_triples(self, triples):
        for triple in triples:
            self._negative_triples.add(triple)
            self._negative_pred[triple[1]].add((triple[0], triple[2]))