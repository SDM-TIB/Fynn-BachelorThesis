from abc import ABC, abstractmethod

class Graph(ABC):
    @abstractmethod
    def clean_uri(self, uri):
        pass

    @abstractmethod
    def resolve_to_uri(self, node):
        pass

    # region All
    @abstractmethod
    def get_all_subjects(self):
        pass
    @abstractmethod
    def get_all_predicates(self):
        pass
    @abstractmethod
    def get_all_objects(self):
        pass

    #endregion

    # region Specific
    @abstractmethod
    def get_triples(self, subject = None, predicate = None, object = None):
        pass

    @abstractmethod
    def get_type(self, subject, type_predicate):
        pass

    @abstractmethod
    def get_adjacent_triples(self, node):
        pass

    @abstractmethod
    def get_edges(self, predicate):
        pass

    @abstractmethod
    def get_objects(self, predicate):
        pass

    @abstractmethod
    def get_predicates(self, subject):
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
    def literal_type(self, ):
        pass

    @abstractmethod
    def is_literal_comp(p):
        pass
    #endregion

    # Modification
    @abstractmethod
    def add_negative_triples(self, triples):
        pass