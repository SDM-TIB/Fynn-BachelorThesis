from KnowledgeGraph.Graph import Graph

class NumericalKG(Graph):
    def __init__(self, path):
        uri_id: dict[str, int] = {}
        self.id_uri: dict[int, str] = {}
        self.adjacency_list = dict[int, list[int]]
        with open(path, "r") as file:
            for line in file:
                pass