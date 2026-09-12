from abc import ABC, abstractmethod

class Graph(ABC):
    @abstractmethod
    def freeze(self, multiprocess: bool, workers: int):
        """
        This function freeze the graph and disables any modifying functions
        :param multiprocess: If multiprocessing should be used
        :param workers: The number of workers to use
        """
        pass

    @abstractmethod
    def clean_uri(self, uri) -> str:
        """
        Converting the given uri to a cleaned version
        :param uri:
        :returns cleaned uri: The uri cleaned to the standard representation used by the graph
        """
        pass

    @abstractmethod
    def resolve_to_uri(self, node):
        """
        Returns a URI representing the given node
        :param node: The graph entity which should be resolved
        """
        pass

    # region Predicates
    @abstractmethod
    def get_all_predicates(self):
        """
        Returns a list of all predicates in the graph
        """
        pass

    @abstractmethod
    def get_balanced_predicate_batches(self):
        """
        Returns a tuple of balanced batches including all predicates
        """
        pass

    def _generate_predicate_batches(self, predicates, workers: int):
        """
        Generates a tuple which contains tuples of predicates which were ordered to be balanced as to distribute load.
        This function only returns correct information after freeze has been called.
        :param predicates: a list of predicates
        :param workers: the number of workers/batches
        :return: a list of tuples con
        """
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
        """
        This function returns all triples in the graph that satisfy the given criteria for 'subject', 'predicate' and 'object'.
        This function is called before and after freeze and has to return correct information immediately after initialization.
        :param subject: the subject of the triple
        :param predicate: the predicate of the triple
        :param object: the object of the triple
        """
        pass

    @abstractmethod
    def get_type(self, subject, type_predicate):
        """
        This function only returns correct information after freeze has been called.
        :param subject:
        :param type_predicate:
        """
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
        """
        Returns all triples that are connected to the given node.
        This function only returns correct information after freeze has been called.
        :param node:
        """
        pass

    @abstractmethod
    def get_edges(self, predicate):
        """
        Returns all edges in the graph that are connected by 'predicate'.
        This function only returns correct information after freeze has been called.
        :param predicate:
        """
        pass

    @abstractmethod
    def get_negative_edges(self, predicate):
        """
        Returns all negative edges in the graph that are connected by 'predicate'.
        This function only returns correct information after freeze has been called.
        :param predicate:
        """
        pass
    #endregion

    #region Literals
    @abstractmethod
    def is_literal(self, object):
        """
        Evaluates the given object and returns a true if the object is a literal and false otherwise.
        :param object:
        """
        pass

    @abstractmethod
    def is_valid_comp(self, node):
        """

        :param node:
        """
        pass

    @abstractmethod
    def literal_type(self, node):
        """

        :param node:
        """
        pass

    @abstractmethod
    def is_literal_comp(self, predicate):
        """

        :param predicate:
        """
        pass
    #endregion

    # Modification
    @abstractmethod
    def add_negative_triples(self, triples):
        """

        :param triples:
        """
        pass