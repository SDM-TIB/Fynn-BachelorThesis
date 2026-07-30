from abc import ABC, abstractmethod

class Graph(ABC):
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

    @abstractmethod
    def get_all_negative_triples(self):
        pass
    #endregion

    # region Specific
    @abstractmethod
    def get_triples(self, subject = None, predicate = None, object = None):
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

    @abstractmethod
    def is_literal(self, object):
        pass

    # Modification
    @abstractmethod
    def remove_triples(self, triples):
        pass

    @abstractmethod
    def add_negative_triples(self, triples):
        pass