from collections import defaultdict
from rdflib import Literal, Graph, RDF
from rdflib.plugins.stores.sparqlstore import SPARQLStore
from KnowledgeGraph.Graph import Graph as KG

RDF_TYPE_URI = str(RDF.type)

class SPARQLKG(KG):
    #TODO: Handle removing triples some way
    def __init__(self, url):
        self._store = SPARQLStore(query_endpoint=url)
        self._graph = Graph(store=self._store)
        self._negative_triples: set[tuple[str, str, str]] = set()
        self._negative_pred = defaultdict(set)
        self._workers: int = 0
        self._type_filter = """
        FILTER(
            !STRSTARTS(STR(?p), "http://www.w3.org/1999/02/22-rdf-syntax-ns#") &&
            !STRSTARTS(STR(?p), "http://www.w3.org/2000/01/rdf-schema#") &&
            !STRSTARTS(STR(?p), "http://www.w3.org/2002/07/owl#") &&
            !STRSTARTS(STR(?p), "http://proton.semanticweb.org/protonsys#")
        )
        """

    def _select(self, query: str) -> list:
        return list(self._graph.query(query))

    def freeze(self, multiprocess: bool, workers: int):
        self._workers = workers

    def clean_uri(self, uri) -> str:
        if isinstance(uri, Literal):
            return f"\"{str(uri)}\""
        return str(uri)


    def resolve_to_uri(self, node):
        return node

    # region Predicates
    def get_all_predicates(self):
        query = (f"""
        SELECT DISTINCT ?p WHERE {{
            ?s ?p ?o .
            {self._type_filter}
        }}
        """)
        return { self.clean_uri(row[0]) for row in self._select(query)}

    def get_balanced_predicate_batches(self):
        query = f"""
        SELECT DISTINCT ?p (COUNT(*) AS ?count) WHERE {{
            ?s ?p ?o .
            {self._type_filter}
        }} GROUP BY ?p
        """
        predicate_counts = [(self.clean_uri(row[0]), int(row[1])) for row in self._select(query)]
        predicate_counts.sort(key=lambda x: x[1], reverse=True)

        batches = [[] for _ in range(self._workers)]
        batch_sizes = [0 for _ in range(self._workers)]

        for predicate, count in predicate_counts:
            batch_min_weight_index = batch_sizes.index(min(batch_sizes))
            batches[batch_min_weight_index].append(predicate)
            batch_sizes[batch_min_weight_index] += count
        return tuple(tuple(batch) for batch in batches)
    #endregion

    # region Specific
    #TODO: Check input data types
    def get_triples(self, subject = None, predicate = None, object = None):
        s_node = f"<{subject}>" if subject else "?s"
        p_node = f"<{predicate}>" if predicate else "?p"
        if object is None:
            o_node = "?o"
        elif self.is_literal(object):
            o_node = f"{object}"
        else:
            o_node = f"<{object}>"

        s_bind = f"BIND({s_node} AS ?s)" if subject else ""
        p_bind = f"BIND({p_node} AS ?p)" if predicate else ""
        o_bind = f"BIND({o_node} AS ?o)" if object else ""

        query = f"""
        SELECT DISTINCT ?s ?p ?o WHERE {{
            {s_node} {p_node} {o_node} .
            {s_bind}
            {p_bind}
            {o_bind}
            {self._type_filter}
        }}
        """
        results = { (self.clean_uri(s), self.clean_uri(p), self.clean_uri(o)) for s, p, o in self._select(query) }
        if not self._negative_triples:
            return results

        if predicate and predicate in self._negative_pred:
            negative_pairs = self._negative_pred.get(predicate, set())
            return { triple for triple in results if (triple[0], triple[2]) not in negative_pairs }

        return results - self._negative_triples

    def get_type(self, subject, type_predicate):
        if self.is_literal(subject):
            return list()
        s_node = f"<{subject}>"
        p_node = f"<{type_predicate}>"
        query = f"SELECT DISTINCT ?o WHERE {{ {s_node} {p_node} ?o }}"
        return { self.clean_uri(value[0]) for value in self._select(query) }

    def get_adjacent_triples(self, node):
        query = f"""
        SELECT DISTINCT ?s ?p ?o WHERE {{
            {{ <{node}> ?p ?o . BIND(<{node}> AS ?s) }}
            UNION
            {{ ?s ?p <{node}> . BIND(<{node}> AS ?o) }}
            {self._type_filter}
        }}
        """
        return { (self.clean_uri(s), self.clean_uri(p), self.clean_uri(o)) for s, p, o in self._select(query) } - self._negative_triples

    def get_edges(self, predicate):
        query = f"SELECT DISTINCT ?s ?o WHERE {{ ?s <{predicate}> ?o }}"
        return {(self.clean_uri(row[0]), self.clean_uri(row[1])) for row in self._select(query)} - self.get_negative_edges(predicate)

    def get_negative_edges(self, predicate):
        return self._negative_pred.get(predicate, set())
    #endregion

    # region Literals
    def is_literal(self, object):
        return object.startswith('"')

    def is_valid_comp(self, node):
        pass

    def literal_type(self, node):
        pass

    def is_literal_comp(p):
        pass
    # endregion

    # Modification
    def remove_triples(self, triples):
        pass

    def add_negative_triples(self, triples):
        for s, p, o in triples:
            s_clean = self.clean_uri(s)
            p_clean = self.clean_uri(p)
            o_clean = self.clean_uri(o)
            self._negative_triples.add((s_clean, p_clean, o_clean))
            self._negative_pred[p_clean].add((s_clean, o_clean))