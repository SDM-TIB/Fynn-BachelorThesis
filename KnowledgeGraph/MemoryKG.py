import sys
import os
from collections import defaultdict
from Utility import get_triples_from, triple_exists

from KnowledgeGraph.Graph import Graph


class MemoryKG(Graph):
    def __init__(self, path, prefix):
        self._prefix = prefix
        self._is_frozen = False

        self._out = defaultdict(set[tuple[str, str]])
        self._in = defaultdict(set[tuple[str, str]])
        self._pred = defaultdict(set[tuple[str, str]])
        self._type = defaultdict(set)
        self._negative_pred = defaultdict(set)

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
                    self._type[self.clean_uri(parts[0])].add(self.clean_uri(parts[2]))
                    continue
                s = self.clean_uri(parts[0])
                p = self.clean_uri(parts[1])
                o = self.clean_uri(parts[2])

                self._add_triple_raw(s, p, o)

    def _add_triple_raw(self, s: str, p: str, o: str):
        self._out[s].add((p, o))
        self._in[o].add((p, s))
        self._pred[p].add((s, o))

    def freeze(self, multiprocess: bool, workers: int):
        if self._is_frozen:
            return
        if multiprocess:
            self._predicate_batches = super()._generate_predicate_batches(self.get_all_predicates(), workers)
        self._is_frozen = True

    def clean_uri(self, uri) -> str:
        token = uri.strip("<> \n\r\t")
        if self._prefix and token.startswith(self._prefix):
            return sys.intern(token[len(self._prefix):])
        return sys.intern(token)

    def resolve_to_uri(self, node):
        if self.is_literal(node):
            return node
        return f"<{self._prefix}{node}>"

    # region Predicates
    def get_all_predicates(self):
        return list(self._pred)

    def get_balanced_predicate_batches(self):
        return self._predicate_batches
    #endregion

    def get_subject_pool(self, maximum_set_size: int, rng):
        size = min(len(list(self._out)), maximum_set_size)
        return rng.sample(list(self._out), size)

    def get_object_pool(self, maximum_set_size: int, rng):
        size = min(len(list(self._in)), maximum_set_size)
        return rng.sample(list(self._in), size)

    # region Specific
    def triple_exists(self, subject, predicate, object) -> bool:
        return triple_exists(subject, predicate, object, self._in, self._out, self._pred)

    def get_triples(self, subject = None, predicate = None, object = None):
        return get_triples_from(subject, predicate, object, self._in, self._out, self._pred)

    def get_types_batched(self, subjects, type_predicate):
        types: dict = { subject: set() for subject in subjects }
        for subject in subjects:
            for t in self.get_type(subject, type_predicate):
                types[subject].add(t)
        return types

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

    # Modification
    def remove_triples(self, triples):
        for s, p, o in triples:
            self._out[s].discard((p, o))
            self._in[o].discard((p, s))
            self._pred[p].discard((s, o))

            if not self._out[s]:
                del self._out[s]

            if not self._in[o]:
                del self._in[o]

            if not self._pred[p]:
                del self._pred[p]

    def add_negative_triples(self, triples):
        if self._is_frozen:
            raise RuntimeError("Negative triples cannot be added after graph has been frozen.")
        for s, p, o in triples:
            self._negative_pred[p].add((s, o))
        self.remove_triples(triples)