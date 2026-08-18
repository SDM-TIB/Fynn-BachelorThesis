import os
from collections import defaultdict

from KnowledgeGraph.Graph import Graph


class NumericalKG(Graph):
    def __init__(self, path, prefix):
        self.mapping_id_str = defaultdict()
        self.mapping_str_id = defaultdict()

        self._prefix = prefix
        self._out = defaultdict(set[tuple[int, int]])
        self._in = defaultdict(set[tuple[int, int]])
        self._pred = defaultdict(set[tuple[int, int]])
        self._type = defaultdict(set)

        # Negative triple stores
        self._negative_triples: set[tuple[int, int, int]] = set()
        self._negative_pred = defaultdict(set)

        # Entity/Predicate tracking sets
        self._subjects: set[int] = set()
        self._predicates: set[int] = set()
        self._objects: set[int] = set()

        if path:
            self._parse_file(path)

    def _parse_file(self, path):
        """Parses standard N-Triples (.nt) files into the graph indices."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Knowledge graph file not found: {path}")

        with open(path, "r", encoding="utf-8") as file:
            next_id = 1
            next_literal_id = -1
            for line in file:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.rstrip(" .").split(maxsplit=2)
                if len(parts) < 3:
                    continue

                if parts[1].strip("<> \n\r\t") == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type':
                    print(self.clean_uri(parts[0]), self.clean_uri(parts[2]))
                    self._type[self.clean_uri(parts[0])].add(self.clean_uri(parts[2]))
                    continue

                s = self.clean_uri(parts[0])
                p = self.clean_uri(parts[1])
                o = self.clean_uri(parts[2])

                next_id, next_literal_id = self._add_triple_raw(s, p, o, next_id, next_literal_id)

    def _add_triple_raw(self, s: str, p: str, o: str, next_id: int, next_literal_id: int) -> tuple[int, int]:
        def add_mapping(value: str) -> int:
            nonlocal next_id
            value_num = self.mapping_str_id.get(value)
            if value_num is None:
                self.mapping_str_id[value] = next_id
                self.mapping_id_str[next_id] = value
                next_id += 1
                return next_id - 1
            return value_num

        s_num = add_mapping(s)
        p_num = add_mapping(p)

        if self._is_literal(o):
            if not self.mapping_str_id.get(o):
                self.mapping_str_id[o] = next_literal_id
                self.mapping_id_str[next_literal_id] = o
                o_num = self.mapping_str_id.get(o)
                next_literal_id -= 1
            else:
                o_num = self.mapping_str_id.get(o)
        else:
            o_num = add_mapping(o)

        self._out[s_num].add((p_num, o_num))
        self._in[o_num].add((p_num, s_num))
        self._pred[p_num].add((s_num, o_num))

        self._subjects.add(s_num)
        self._predicates.add(p_num)
        self._objects.add(o_num)
        return next_id, next_literal_id

    def _is_literal(self, object):
        return object.startswith('"')

    def clean_uri(self, uri):
        if uri is None:
            return None
        token = uri.strip("<> \n\r\t")
        if self.prefix and token.startswith(self.prefix):
            return token[len(self.prefix):]
        return token

    def resolve_to_uri(self, node):
        return f"<{self._prefix}{self.mapping_id_str[node]}>"

    # region All
    def get_all_subjects(self):
        return self._subjects

    def get_all_predicates(self):
        return self._predicates

    def get_all_objects(self):
        return self._objects

    #endregion

    # region Specific
    def get_triples(self, subject = None, predicate = None, object = None):
        if subject is not None and predicate is not None and object is not None:
            if (predicate, object) in self._out.get(subject, set()):
                return {(subject, predicate, object)} if (predicate, object) in self._out.get(subject, set()) else set()
            return set()

        if subject is not None:
            pairs = self._out.get(subject, set())
            return {
                (subject, p, o)
                for p, o in pairs
                if (predicate is None or p == predicate) and (object is None or o == object)
            }

        if object is not None:
            pairs = self._in.get(object, set())
            return {
                (s, p, object)
                for p, s in pairs
                if (predicate is None or p == predicate) and (subject is None or s == subject)
            }

        if predicate is not None:
            pairs = self._pred.get(predicate, set())
            return {
                (s, predicate, o)
                for s, o in pairs
                if (subject is None or s == subject) and (object is None or o == object)
            }

        all_triples = set()
        for p, pairs in self._pred.items():
            for s, o in pairs:
                all_triples.add((s, p, o))
        return all_triples

    def get_type(self, subject, type_predicate):
        return self._type[self.clean_uri(subject)]

    def get_adjacent_triples(self, node):
        outgoing = {(node, p, o) for p, o in self._out.get(node, set())}
        incoming = {(s, p, node) for p, s in self._in.get(node, set())}
        return outgoing | incoming

    def get_edges(self, predicate) -> set[tuple[int, int]]:
        return self._pred.get(predicate, set())

    def get_objects(self, predicate):
        return {o for _, o in self._pred.get(predicate, set())}

    def get_predicates(self, subject):
        return {p for p, _ in self._out.get(subject, set())}

    def get_negative_edges(self, predicate):
        return self._negative_pred.get(predicate, set())
    #endregion

    # region Literals
    def is_literal(self, object):
        return object < 0

    def is_valid_comp(self, node):
        pass

    def literal_type(self, ):
        pass

    def is_literal_comp(p):
        pass
    # endregion

    # Modification
    def remove_triples(self, triples):
        for s, p, o in triples:
            s = self.mapping_str_id.get(s)
            p = self.mapping_str_id.get(p)
            o = self.mapping_str_id.get(o)
            self._out[s].discard((p, o))
            self._in[o].discard((p, s))
            self._pred[p].discard((s, o))

            if not self._out[s]:
                del self._out[s]
                self._subjects.discard(s)

            if not self._in[o]:
                del self._in[o]
                self._objects.discard(o)

            if not self._pred[p]:
                del self._pred[p]
                self._predicates.discard(p)

    def add_negative_triples(self, triples):
        for s, p, o in triples:
            s_num = self.mapping_str_id.get(s)
            o_num = self.mapping_str_id.get(o)
            p_num = self.mapping_str_id.get(p)
            self._negative_triples.add((s_num, p_num, o_num))
            self._negative_pred[p_num].add((s_num, o_num))