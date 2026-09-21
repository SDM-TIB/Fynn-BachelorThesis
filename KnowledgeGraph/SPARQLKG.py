import os
from typing import override

import immutables
import urllib3
import orjson
from collections import defaultdict
from rdflib import RDF
from KnowledgeGraph.Graph import Graph as KG

RDF_TYPE_URI = str(RDF.type)

class SPARQLKG(KG):
    def __init__(self, url, multiprocess: bool, workers: int):
        self._endpoint_url = url
        self._client = None
        self._client_pid = None
        self._workers: int = workers
        self._type_filter = """
                FILTER(
                    !STRSTARTS(STR(?p), "http://www.w3.org/1999/02/22-rdf-syntax-ns#") &&
                    !STRSTARTS(STR(?p), "http://www.w3.org/2000/01/rdf-schema#") &&
                    !STRSTARTS(STR(?p), "http://www.w3.org/2002/07/owl#") &&
                    !STRSTARTS(STR(?p), "http://proton.semanticweb.org/protonsys#")
                )
                """
        # Mutable for initialization
        self._negative_triples: set[tuple[str, str, str]] = set()
        self._negative_pred: defaultdict = defaultdict(set)
        # Immutable for multiprocess compatibility
        # self._negative_pred = immutables.Map()
        # self._negative_triples: tuple[tuple[str, str, str]] = tuple()

    @property
    def client(self):
        pid = os.getpid()

        if self._client is None or self._client_pid != pid:
            self._client = urllib3.PoolManager()
            self._client_pid = pid

        return self._client

    def __getstate__(self):
        state = self.__dict__.copy()
        state["_client"] = None
        state["_client_pid"] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._client = None
        self._client_pid = None

    def _select(self, query: str) -> list:
        #TODO: Improve error handling
        response = self.client.request("POST", self._endpoint_url, body=query.encode("utf-8"), headers={"Accept": "application/sparql-results+json", "Content-Type": "application/sparql-query"})
        if response.status != 200:
            print(f"Query: {query}")
            print(f"Response: {response}")
            print(f": {response.status}")
            raise RuntimeError(response.status)
        data = orjson.loads(response.data)
        variables = data.get("head", {}).get("vars", [])
        bindings = data.get("results", {}).get("bindings", {})
        return [tuple(self.to_internal_format(binding[variable]) for variable in variables if variable in binding) for binding in bindings]

    def _ask(self, query: str) -> bool:
        response = self.client.request("POST", self._endpoint_url, body=query.encode("utf-8"),
                                       headers={"Accept": "application/sparql-results+json",
                                                "Content-Type": "application/sparql-query"})
        if response.status != 200:
            print(f"Query: {query}")
            print(f"Response: {response}")
            print(f": {response.status}")
            raise RuntimeError(response.status)
        data = orjson.loads(response.data)
        return data["boolean"]

    def freeze(self, multiprocess: bool, workers: int):
        # self._negative_pred = immutables.Map(
        #     {predicate: tuple(pairs) for predicate, pairs in self._negative_pred_mutable.items()}
        # )
        # self._negative_triples = tuple(self._negative_triples_mutable)
        #
        # del self._negative_pred_mutable
        # del self._negative_triples_mutable
        pass

    def to_internal_format(self, binding):
        if binding["type"] == "literal":
            if "datatype" in binding:
                return f'"{binding["value"]}"^^{binding["datatype"]}'
            return f'"{binding["value"]}"^^{"http://www.w3.org/2001/XMLSchema#string"}'
        return binding["value"]

    def clean_uri(self, uri) -> str:
        return uri


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
        predicate_counts = [(self.clean_uri(row[0]), int(row[1].split('"')[1])) for row in self._select(query)]
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

    def _format_pattern_term(self, term: str, name_dict: dict) -> str:
        if term in name_dict:
            return f"<{name_dict[term]}>"
        return f"?{term}"

    @override
    def patterns_in_graph(self, body: set[tuple], name_dict: dict) -> bool:
        #TODO: Add handling for negative examples
        if not body:
            return True

        variables = sorted({
            term for subject, _, object in body for term in (subject, object) if term not in name_dict
        })

        patterns = []

        for subject, predicate, object in body:
            s = self._format_pattern_term(subject, name_dict)
            o = self._format_pattern_term(object, name_dict)
            patterns.append(f"{s} <{predicate}> {o} .")

        graph_pattern = "\n".join(patterns)

        if not variables:
            query = f"""
            ASK WHERE {{
                {graph_pattern}
            }}
            """
            return self._ask(query)

        select_variables = " ".join(f"?{variable}" for variable in variables)

        query = f"""
        SELECT DISTINCT {select_variables} WHERE {{
            {graph_pattern}
        }}
        """
        return len(self._select(query)) > 0
    #endregion

    # region Literals
    def is_literal(self, object):
        return object.startswith('"')

    def is_valid_comp(self, node):
        pass

    def literal_type(self, node):
        pass

    def is_literal_comp(self, predicate):
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