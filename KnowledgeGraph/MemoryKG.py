import sys
import immutables
import os
from collections import defaultdict
from Utility import get_triples_from

from KnowledgeGraph.Graph import Graph


class MemoryKG(Graph):
    def __init__(self, path, prefix):
        self._prefix = prefix
        self._is_frozen = False

        # Mutable dicts for initialization process
        self._out_mutable = defaultdict(set[tuple[str, str]])
        self._in_mutable = defaultdict(set[tuple[str, str]])
        self._pred_mutable = defaultdict(set[tuple[str, str]])
        self._type_mutable = defaultdict(set)
        self._predicates_mutable = set()
        self._negative_triples_mutable: set[tuple[str, str, str]] = set()
        self._negative_pred_mutable = defaultdict(set)

        # Immutable versions for rule mining
        self._out = immutables.Map()
        self._in = immutables.Map()
        self._pred = immutables.Map()
        self._type = immutables.Map()
        self._negative_pred = immutables.Map()
        self._negative_triples: tuple[tuple[str, str, str]] = tuple()
        self._predicates: tuple[str] = tuple()
        self._predicate_batches: tuple[tuple[str]] = tuple()

        if path:
            self._parse_file(path)

    def _parse_file(self, path: str):
        """Parses standard N-Triples (.nt) files into the graph indices."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Knowledge graph file not found: {path}")

        with open(path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Parse subject, predicate, object from N-Triples line
                parts = line.rstrip(" .").split(maxsplit=2)
                if len(parts) < 3:
                    continue

                if parts[1].strip("<> \n\r\t") == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type':
                    # print(self.clean_uri(parts[0]), self.clean_uri(parts[2]))
                    self._type_mutable[self.clean_uri(parts[0])].add(self.clean_uri(parts[2]))
                    continue
                s = self.clean_uri(parts[0])
                p = self.clean_uri(parts[1])
                o = self.clean_uri(parts[2])

                self._add_triple_raw(s, p, o)

    def _add_triple_raw(self, s: str, p: str, o: str):
        self._out_mutable[s].add((p, o))
        self._in_mutable[o].add((p, s))
        self._pred_mutable[p].add((s, o))
        self._predicates_mutable.add(p)

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

        self._is_frozen = True

    def clean_uri(self, uri) -> str:
        token = uri.strip("<> \n\r\t")
        if self._prefix and token.startswith(self._prefix):
            return sys.intern(token[len(self._prefix):])
        return sys.intern(token)

    def resolve_to_uri(self, node):
        return f"<{self._prefix}{node}>"

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
        return self._type.get(self.clean_uri(subject), ())


    def get_adjacent_triples(self, node):
        for p, o in self._out.get(node, ()):
            yield node, p, o
        for p, s in self._in.get(node, ()):
            yield s, p, node

    def get_edges(self, predicate) -> set[tuple[str, str]]:
        return self._pred.get(predicate, ())

    def get_objects(self, predicate):
        return {o for _, o in self._pred.get(predicate, ())}

    def get_predicates(self, subject):
        return {p for p, _ in self._out.get(subject, ())}

    def get_negative_edges(self, predicate):
        return self._negative_pred.get(predicate, ())
    #endregion

    # region Literals
    def is_literal(self, object):
        return object.startswith('"')

    def is_valid_comp(self, node):
        pass

    def literal_type(self, node):
        if "^^" in node:
            full_type = node.rsplit("^^", 1)[1]
            type = full_type.rsplit("#", 1)[1]
            print(type)
            return type
        return ""

    def is_literal_comp(p):
        pass
    # endregion

    # Modification
    def remove_triples(self, triples):
        for s, p, o in triples:
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
        if self._is_frozen:
            raise RuntimeError("Negative triples cannot be added after graph has been frozen.")
        for s, p, o in triples:
            self._negative_triples_mutable.add((s, p, o))
            self._negative_pred_mutable[p].add((s, o))
        self.remove_triples(triples)