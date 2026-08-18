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

    def clean_uri(self, uri):
        if isinstance(uri, Literal):
            return f"\"{str(uri)}\""
        return str(uri)


    def resolve_to_uri(self, node):
        #TODO: Implement
        return node

    # region All
    def get_all_subjects(self):
        query = (f"""
        SELECT DISTINCT ?s WHERE {{
            ?s ?p ?o .
            {self._type_filter}
        }}
        """)
        return {row[0] for row in self._select(query)}

    def get_all_predicates(self):
        query = (f"""
        SELECT DISTINCT ?p WHERE {{
            ?s ?p ?o .
            {self._type_filter}
        }}
        """)
        return {row[0] for row in self._select(query)}

    def get_all_objects(self):
        # query = "SELECT DISTINCT ?o WHERE { ?s ?p ?o }"
        query = (f"""
        SELECT DISTINCT ?o WHERE {{
            ?s ?p ?o .
            {self._type_filter}
        }}
        """)
        return {row[0] for row in self._select(query)}

    #endregion

    # region Specific
    #TODO: Check input data types
    def get_triples(self, subject = None, predicate = None, object = None):
        # s_node = self._to_node(subject)
        # p_node = self._to_node(predicate)
        # o_node = self._to_node(object)
        # triples = set(self._graph.triples((s_node, p_node, o_node)))
        # triples = {triple for triple in triples if str(triple[1]) != RDF_TYPE_URI}
        # return triples
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
        return self._select(query)

    def get_type(self, subject, type_predicate):
        # print(subject, type_predicate)
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
        return self._select(query)

    def get_edges(self, predicate):
        query = f"SELECT DISTINCT ?s ?o WHERE {{ ?s <{predicate}> ?o }}"
        return {(row[0], row[1]) for row in self._select(query)}

    def get_objects(self, predicate):
        query = f"SELECT DISTINCT ?o WHERE {{ ?s <{predicate}> ?o }}"
        return {row[0] for row in self._select(query)}

    def get_predicates(self, subject):
        query = f"""
        SELECT DISTINCT ?p WHERE {{
            <{subject}> ?p ?o .
            {self._type_filter}
        }}"""
        return {row[0] for row in self._select(query)}

    def get_negative_edges(self, predicate):
        return self._negative_pred.get(predicate, set())
    #endregion

    # region Literals
    def is_literal(self, object):
        # print(isinstance(object, str))
        # return isinstance(object, Literal)
        # print(object)
        # print(object.startswith('http://'))
        # return not object.startswith('http://')
        return object.startswith('"')

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