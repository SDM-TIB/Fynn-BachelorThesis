import os
from collections import defaultdict
from typing import Optional

from KnowledgeGraph.Graph import Graph
from Utility import clean_uri


class MemoryKG(Graph):
    def __init__(self, path, prefix):
        self._out = defaultdict(set[tuple[str, str]])
        self._in = defaultdict(set[tuple[str, str]])
        self._pred = defaultdict(set[tuple[str, str]])

        # Negative triple stores
        self._negative_triples: set[tuple[str, str, str]] = set()
        self._negative_pred = defaultdict(set)  # p -> {(s, o)}

        # Entity/Predicate tracking sets
        self._subjects: set[str] = set()
        self._predicates: set[str] = set()
        self._objects: set[str] = set()

        if path:
            self._parse_file(path, prefix)

    def _parse_file(self, path: str, prefix: Optional[str]):
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

                s = clean_uri(parts[0], prefix)
                p = clean_uri(parts[1], prefix)
                o = clean_uri(parts[2], prefix)

                self._add_triple_raw(s, p, o)

    def _add_triple_raw(self, s: str, p: str, o: str):
        self._out[s].add((p, o))
        self._in[o].add((p, s))
        self._pred[p].add((s, o))

        self._subjects.add(s)
        self._predicates.add(p)
        self._objects.add(o)

    # region All
    def get_all_subjects(self):
        return self._subjects

    def get_all_predicates(self):
        return self._predicates

    def get_all_objects(self):
        return self._objects

    def get_all_negative_triples(self):
        return self._negative_triples
    #endregion

    # region Specific
    def get_triples(self, subject = None, predicate = None, object = None):
        if subject is not None and predicate is not None and object is not None:
            if (object, predicate) in self._out.get(subject, set()):
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

    def get_edges(self, predicate) -> set[tuple[str, str]]:
        return self._pred.get(predicate, set())

    def get_objects(self, predicate):
        return {o for _, o in self._pred.get(predicate, set())}

    def get_predicates(self, subject):
        return {p for p, _ in self._out.get(subject, set())}

    def get_negative_edges(self, predicate):
        return self._negative_pred.get(predicate, set())
    #endregion

    def is_literal(self, object):
        return object.startswith('"')

    # Modification
    def remove_triples(self, triples):
        for s, p, o in triples:
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
            self._negative_triples.add((s, p, o))
            self._negative_pred[p].add((s, o))