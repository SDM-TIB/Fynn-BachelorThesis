import gc
import os
import immutables
from collections import defaultdict
from KnowledgeGraph.Graph import Graph
from Utility import get_triples_from

class NumericalKG(Graph):
    def __init__(self, path, prefix):
        self._prefix = prefix
        self._is_frozen = False

        self.mapping_id_str = defaultdict()
        self.mapping_str_id = defaultdict()

        # Mutable for KG creation
        self._out_mutable = defaultdict(set[tuple[int, int]])
        self._in_mutable = defaultdict(set[tuple[int, int]])
        self._pred_mutable = defaultdict(set[tuple[int, int]])
        self._type_mutable = defaultdict(set)
        self._negative_triples_mutable: set[tuple[int, int, int]] = set()
        self._negative_pred_mutable = defaultdict(set)
        self._predicates_mutable: set[int] = set()

        # Immutable versions for rule mining
        self._out = immutables.Map()
        self._in = immutables.Map()
        self._pred = immutables.Map()
        self._type = immutables.Map()
        self._negative_pred = immutables.Map()
        self._negative_triples: tuple[tuple[int, int, int]] = tuple()
        self._predicates: tuple[int] = tuple()
        self._predicate_batches: tuple[tuple[int]] = tuple()

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
                    self._type_mutable[self.clean_uri(parts[0])].add(self.clean_uri(parts[2]))
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

        self._out_mutable[s_num].add((p_num, o_num))
        self._in_mutable[o_num].add((p_num, s_num))
        self._pred_mutable[p_num].add((s_num, o_num))

        self._predicates_mutable.add(p_num)
        return next_id, next_literal_id

    def _is_literal(self, object):
        return object.startswith('"')

    def freeze(self, multiprocess: bool, workers: int):
        if self._is_frozen:
            return

        self._out = immutables.Map(
            {subject: tuple(pairs) for subject, pairs in self._out_mutable.items()}
        )
        self._in = immutables.Map(
            {object: tuple(pairs) for object, pairs in self._in_mutable.items()}
        )
        self._pred = immutables.Map(
            {predicate: tuple(pairs) for predicate, pairs in self._pred_mutable.items()}
        )
        self._type = immutables.Map(
            {node: tuple(pairs) for node, pairs in self._type_mutable.items()}
        )
        self._negative_pred = immutables.Map(
            {predicate: tuple(pairs) for predicate, pairs in self._negative_pred_mutable.items()}
        )
        self._negative_triples = tuple(self._negative_triples_mutable)
        if multiprocess:
            self._predicate_batches = super()._generate_predicate_batches(self._predicates_mutable, workers)
        else:
            self._predicates = tuple(self._predicates_mutable)

        del self._out_mutable
        del self._in_mutable
        del self._pred_mutable
        del self._type_mutable
        del self._negative_pred_mutable
        del self._negative_triples_mutable
        del self._predicates_mutable
        del self.mapping_str_id
        gc.collect()
        self._is_frozen = True

    def clean_uri(self, uri) -> str:
        token = uri.strip("<> \n\r\t")
        if self._prefix and token.startswith(self._prefix):
            return token[len(self._prefix):]
        return token

    def resolve_to_uri(self, node):
        return f"{self._prefix}{self.mapping_id_str[node]}"

    # region Predicates
    def get_all_predicates(self):
        return self._predicates

    def get_balanced_predicate_batches(self):
        return self._predicate_batches
    #endregion

    # region Specific
    def get_triples(self, subject = None, predicate = None, object = None):
        if not self._is_frozen:
            return get_triples_from(subject, predicate, object, self._in_mutable, self._out_mutable, self._pred_mutable)
        return get_triples_from(subject, predicate, object, self._in, self._out, self._pred)

    def get_type(self, subject, type_predicate):
        return self._type.get(subject, ())

    def get_adjacent_triples(self, node):
        for p, o in self._out.get(node, ()):
            yield node, p, o
        for p, s in self._in.get(node, ()):
            yield s, p, node

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

    def literal_type(self, node):
        pass

    def is_literal_comp(self, predicate):
        pass
    # endregion

    # Modification
    def remove_triples(self, triples):
        if self._is_frozen:
            raise RuntimeError("Cannot remove triples from frozen KnowledgeGraph")
        for s, p, o in triples:
            s = self.mapping_str_id.get(s)
            p = self.mapping_str_id.get(p)
            o = self.mapping_str_id.get(o)
            self._out_mutable[s].discard((p, o))
            self._in_mutable[o].discard((p, s))
            self._pred_mutable[p].discard((s, o))

            if not self._out_mutable[s]:
                del self._out_mutable[s]

            if not self._in_mutable[o]:
                del self._in_mutable[o]

            if not self._pred_mutable[p]:
                del self._pred_mutable[p]
                self._predicates_mutable.discard(p)

    def add_negative_triples(self, triples):
        for s, p, o in triples:
            s_num = self.mapping_str_id.get(s)
            o_num = self.mapping_str_id.get(o)
            p_num = self.mapping_str_id.get(p)
            self._negative_triples_mutable.add((s_num, p_num, o_num))
            self._negative_pred_mutable[p_num].add((s_num, o_num))