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

    def patterns_in_graph(self, body: set[tuple], name_dict: dict) -> bool:
        """Helper function to check if triple patterns are instantiable in KG."""
        if not body:
            return True

        solutions = [name_dict]
        handled_patterns = set()

        while len(handled_patterns) < len(body):
            best_pattern = None
            for pattern in body:
                if pattern in handled_patterns:
                    continue
                if pattern[0] in solutions[0] and pattern[2] in solutions[0]:
                    best_pattern = pattern
                    break

            if best_pattern:
                s_var, p, o_var = best_pattern
                new_solutions = []
                for sol in solutions:
                    if bool(self.get_triples(subject=sol[s_var], predicate=p, object=sol[o_var])):
                        new_solutions.append(sol)
                solutions = new_solutions
                handled_patterns.add(best_pattern)
            else:
                for pattern in body:
                    if pattern in handled_patterns:
                        continue
                    if pattern[0] in solutions[0] or pattern[2] in solutions[0]:
                        best_pattern = pattern
                        break

                if not best_pattern:
                    for pattern in body:
                        if pattern not in handled_patterns:
                            best_pattern = pattern
                            break

                if best_pattern:
                    s_var, p, o_var = best_pattern
                    new_solutions = []
                    for sol in solutions:
                        s_bound = sol.get(s_var)
                        o_bound = sol.get(o_var)

                        matches = self.get_triples(subject=s_bound, predicate=p, object=o_bound)
                        for m_s, m_p, m_o in matches:
                            new_sol = sol.copy()
                            new_sol[s_var] = m_s
                            new_sol[o_var] = m_o
                            new_solutions.append(new_sol)
                    solutions = new_solutions
                    handled_patterns.add(best_pattern)

            if not solutions:
                return False

        return True

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