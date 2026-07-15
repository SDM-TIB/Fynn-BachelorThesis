from abc import ABC, abstractmethod

class Graph(ABC):
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
    def get_edges(self, predicate):
        pass

    @abstractmethod
    def get_objects(self, predicate):
        pass
    @abstractmethod
    def get_predicates(self, subject):
        pass