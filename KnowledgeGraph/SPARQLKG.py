import os
import sys
from math import ceil
from typing import override
import urllib3
import orjson
from collections import defaultdict
from rdflib import RDF
from KnowledgeGraph.Graph import Graph as KG

RDF_TYPE_URI = str(RDF.type)


def to_internal_format(binding):
    if binding["type"] == "literal":
        if "datatype" in binding:
            return f'"{binding["value"]}"^^{binding["datatype"]}'
        return f'"{binding["value"]}"'
    return binding["value"]

class SPARQLKG(KG):
    def __init__(self, url, prefix: str, multiprocess: bool, workers: int):
        self._prefix: str = prefix
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
        self._negative_triples: set[tuple[str, str, str]] = set()
        self._negative_pred: defaultdict = defaultdict(set)

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

    def _send_query(self, query: str):
        response = self.client.request("POST", self._endpoint_url, body=query.encode("utf-8"),
                                       headers={"Accept": "application/sparql-results+json",
                                                "Content-Type": "application/sparql-query"})
        if response.status != 200:
            print(f"Query: {query}")
            print(f"Response: {response}")
            print(f"Status: {response.status}")
            print(f"Message: {response.data.decode('utf-8')}")
            raise RuntimeError(response.status)
        data = orjson.loads(response.data)
        del response
        return data

    def _select(self, query: str) -> list:
        data = self._send_query(query)
        variables = data.get("head", {}).get("vars", [])
        bindings = data.get("results", {}).get("bindings", {})
        return [tuple(to_internal_format(binding[variable]) for variable in variables if variable in binding) for binding in bindings]

    def _ask(self, query: str) -> bool:
        data = self._send_query(query)
        return data["boolean"]

    def freeze(self, multiprocess: bool, workers: int):
        pass

    def clean_uri(self, uri) -> str:
        return sys.intern(uri.removeprefix(self._prefix))


    def resolve_to_uri(self, node):
        if self.is_literal(node) or node.startswith("http"):
            return node
        return f"{self._prefix}{node}"

    def _to_query_format(self, value):
        if self.is_literal(value):
            return value
        return f"<{self.resolve_to_uri(value)}>"

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

    def get_subject_pool(self, maximum_set_size: int, rng):
        # rng can not be considered here so this introduces unseeded randomness
        query = (f"""
        SELECT DISTINCT ?s WHERE {{
            ?s ?p ?o .
        }}
        ORDER BY RAND() LIMIT {maximum_set_size}
        """)
        return { self.clean_uri(row[0]) for row in self._select(query)}

    def get_object_pool(self, maximum_set_size: int, rng):
        # rng can not be considered here so this introduces unseeded randomness
        query = (f"""
        SELECT DISTINCT ?o WHERE {{
            ?s ?p ?o .
        }}
        ORDER BY RAND() LIMIT {maximum_set_size}
        """)
        return { self.clean_uri(row[0]) for row in self._select(query)}

    # region Specific
    def triple_exists(self, subject, predicate, object) -> bool:
        # Never used in SPARQL or Hybrid approach
        pass

    def get_triples(self, subject = None, predicate = None, object = None):
        s_node = f"<{self.resolve_to_uri(subject)}>" if subject else "?s"
        p_node = f"<{self.resolve_to_uri(predicate)}>" if predicate else "?p"
        if object is None:
            o_node = "?o"
        elif self.is_literal(object):
            o_node = f"{object}"
        else:
            o_node = f"<{self.resolve_to_uri(object)}>"

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

        return results - self._negative_triples

    def get_type(self, subject, type_predicate):
        if self.is_literal(subject):
            return list()
        s_node = f"<{self.resolve_to_uri(subject)}>"
        p_node = f"<{type_predicate}>"
        query = f"SELECT DISTINCT ?o WHERE {{ {s_node} {p_node} ?o }}"
        return { self.clean_uri(value[0]) for value in self._select(query) }

    def get_types_batched(self, subjects, type_predicate) -> dict:
        subjects = { subject for subject in subjects if not self.is_literal(subject) }
        if not subjects:
            return {}
        subjects = list(subjects)
        batch_size = 2500
        batches = ceil(len(subjects)/batch_size)
        result = {subject: set() for subject in subjects}
        for i in range(0, batches):
            batch = subjects[i*batch_size:(i+1)*batch_size]
            values = " ".join(f"<{self.resolve_to_uri(subject)}>" for subject in batch)
            query = f"""
            SELECT DISTINCT ?s ?o WHERE {{
                VALUES ?s {{ {values} }}
                ?s <{type_predicate}> ?o .
            }}
            """
            for s, t in self._select(query):
                result[self.clean_uri(s)].add(self.clean_uri(t))
        return result

    def get_adjacent_triples(self, node):
        if self.is_literal(node):
            query = f"""
            SELECT DISTINCT ?s ?p  WHERE {{
                ?s ?p {node} .
                {self._type_filter}
            }}
            """
            return {(self.clean_uri(s), self.clean_uri(p), node) for s, p in
                    self._select(query)} - self._negative_triples
        query = f"""
        SELECT DISTINCT ?s ?p ?o WHERE {{
            {{ <{self.resolve_to_uri(node)}> ?p ?o . BIND(<{self.resolve_to_uri(node)}> AS ?s) }}
            UNION
            {{ ?s ?p <{self.resolve_to_uri(node)}> . BIND(<{self.resolve_to_uri(node)}> AS ?o) }}
            {self._type_filter}
        }}
        """
        return { (self.clean_uri(s), self.clean_uri(p), self.clean_uri(o)) for s, p, o in self._select(query) } - self._negative_triples

    def get_edges(self, predicate):
        query = f"SELECT DISTINCT ?s ?o WHERE {{ ?s <{self.resolve_to_uri(predicate)}> ?o }}"
        return {(self.clean_uri(row[0]), self.clean_uri(row[1])) for row in self._select(query)} - self.get_negative_edges(predicate)

    def get_negative_edges(self, predicate):
        return self._negative_pred.get(predicate, set())

    def _format_pattern_term(self, term: str, name_dict: dict) -> str:
        if term in name_dict:
            return f"{self._to_query_format(name_dict[term])}"
        return f"?{term}"

    @override
    def patterns_in_graph(self, body: set[tuple], name_dict: dict) -> bool:
        if not body:
            return True

        patterns = []
        filters = []
        for subject, predicate, object in body:
            s = self._format_pattern_term(subject, name_dict)
            o = self._format_pattern_term(object, name_dict)
            patterns.append(f"{s} <{self.resolve_to_uri(predicate)}> {o} .")
            if predicate in self._negative_pred:
                if subject in name_dict and object in name_dict:
                    if (subject, object) in self._negative_pred[predicate]:
                        return False
                    continue
                if subject in name_dict:
                    negative_objects = set()
                    for negative_s, negative_o in self._negative_pred[predicate]:
                        if negative_s == name_dict[subject]:
                            if self.is_literal(negative_o):
                                negative_objects.add(negative_o)
                            else:
                                negative_objects.add(f"(<{self.resolve_to_uri(negative_o)}>)")
                    values = "\n".join(negative_o for negative_o in negative_objects)
                    filters.append(f"""
                        FILTER NOT EXISTS {{
                            VALUES (?negative_o) {{
                                {values}
                            }}
                            FILTER (?negative_o = {o})
                        }}
                        """)
                    continue
                if object in name_dict:
                    values = "\n".join(
                        f"(<{self.resolve_to_uri(negative_s)}>)" for negative_s, negative_o in self._negative_pred[predicate] if negative_o == name_dict[object])
                    filters.append(f"""
                        FILTER NOT EXISTS {{
                            VALUES (?negative_s) {{
                                {values}
                            }}
                            FILTER (?negative_s = {s})
                        }}
                        """)
                    continue
                values = "\n".join(f"(<{self.resolve_to_uri(negative_s)}> "
                                   f"{negative_o})" if self.is_literal(negative_o) else f"(<{self.resolve_to_uri(negative_s)}> "
                                                                                         f"<{self.resolve_to_uri(negative_o)}>)" for negative_s, negative_o in self._negative_pred[predicate])
                filters.append(f"""
                    FILTER NOT EXISTS {{
                        VALUES (?negative_s ?negative_o) {{
                            {values}
                        }}
                        FILTER (
                            ?negative_s = {s} &&
                            ?negative_o = {o}
                        )
                    }}
                    """)

        graph_pattern = "\n".join(patterns)
        filter_pattern = "\n".join(filters)
        query = f"""
        ASK WHERE {{
            {graph_pattern}
            {filter_pattern}
        }}
        """
        return self._ask(query)
    #endregion

    #region Negative Triples
    def add_negative_triples(self, triples):
        for s, p, o in triples:
            s_clean = self.clean_uri(s)
            p_clean = self.clean_uri(p)
            o_clean = self.clean_uri(o)
            self._negative_triples.add((s_clean, p_clean, o_clean))
            self._negative_pred[p_clean].add((s_clean, o_clean))
    #endregion