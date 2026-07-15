from KnowledgeGraph.Graph import Graph

class MemoryKG(Graph):
    def __init__(self, path, prefix):
        if prefix is None:
            with open(path, "r") as file:
                for line in file:
                    split = line.split()
                    split[0]
                    split[1]
                    split[2]
        else:
            with open(path, "r") as file:
                for line in file:
                    split = line.split()