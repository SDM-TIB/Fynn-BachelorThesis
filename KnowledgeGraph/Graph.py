from abc import ABC, abstractmethod

class Graph(ABC):
    @abstractmethod
    def freeze(self, multiprocess: bool, workers: int):
        pass

    @abstractmethod
    def clean_uri(self, uri) -> str:
        pass

    @abstractmethod
    def resolve_to_uri(self, node):
        pass

    # region Predicates
    @abstractmethod
    def get_all_predicates(self):
        pass

    @abstractmethod
    def get_balanced_predicate_batches(self):
        pass

    def _generate_predicate_batches(self, predicates, workers: int):
        predicate_counts = [(predicate, len(self.get_edges(predicate))) for predicate in predicates]
        predicate_counts.sort(key=lambda x: x[1], reverse=True)

        batches = [[] for _ in range(workers)]
        batch_sizes = [0 for _ in range(workers)]

        for predicate, count in predicate_counts:
            batch_min_weight_index = batch_sizes.index(min(batch_sizes))
            batches[batch_min_weight_index].append(predicate)
            batch_sizes[batch_min_weight_index] += count
        return tuple(tuple(batch) for batch in batches)
    #endregion

    # region Specific
    @abstractmethod
    def get_triples(self, subject = None, predicate = None, object = None):
        pass

    @abstractmethod
    def get_type(self, subject, type_predicate):
        pass

    # A batched approach seems to only be faster for SPARQL and only if run as a single process

    # def expand_paths(self, rule_dict: dict, paths: set[Path], ontology, type_predicate: str):
    #     path_frontier_map = []
    #     frontiers_to_fetch = set()
    #
    #     for path in paths:
    #         frontier = path.frontiers_closed_rule()
    #         if frontier and not self.is_literal(frontier):
    #             path_frontier_map.append((path, frontier))
    #             frontiers_to_fetch.add(frontier)
    #
    #     if not frontiers_to_fetch:
    #         return
    #
    #     adjacent_map = self.get_adjacent_triples_bulk(list(frontiers_to_fetch))
    #
    #     for path, frontier in path_frontier_map:
    #         adjacent_triples = adjacent_map.get(frontier, set())
    #         frontier = path.frontiers_closed_rule()
    #         path_body = path.body
    #         path_head = path.head
    #         nodes = path.get_nodes()
    #
    #         for s, p, o in adjacent_triples:
    #             if p == type_predicate:
    #                 continue
    #
    #             triple = (s, p, o)
    #             if triple in path_body or triple == path_head:
    #                 continue
    #
    #             e = o if s == frontier else s
    #
    #             if e != frontier and e in nodes:
    #                 continue
    #
    #             is_subject = (s == e)
    #             if ontology.fits_domain_range(triple, self, type_predicate, check_domain=is_subject, check_range=not is_subject):
    #                 new_path = path.copy()
    #                 new_path.body.add(triple)
    #                 rule = new_path.to_rule_closed_rule(self.resolve_to_uri)
    #
    #                 if rule in rule_dict:
    #                     rule_dict[rule].add(new_path)
    #                 else:
    #                     rule_dict[rule] = {new_path}
    #
    # def get_adjacent_triples_bulk(self, nodes):
    #     return {node: self.get_adjacent_triples(node) for node in nodes}

    @abstractmethod
    def get_adjacent_triples(self, node):
        pass

    @abstractmethod
    def get_edges(self, predicate):
        pass

    @abstractmethod
    def get_negative_edges(self, predicate):
        pass
    #endregion

    #region Literals
    @abstractmethod
    def is_literal(self, object):
        pass

    @abstractmethod
    def is_valid_comp(self, node):
        pass

    @abstractmethod
    def literal_type(self, node):
        pass

    @abstractmethod
    def is_literal_comp(p):
        pass
    #endregion

    # Modification
    @abstractmethod
    def add_negative_triples(self, triples):
        pass