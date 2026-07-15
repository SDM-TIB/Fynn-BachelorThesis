import argparse
import time
from KnowledgeGraph.Graph import Graph
from pathlib import Path

parser = argparse.ArgumentParser(description="")

parser.add_argument("--kg-name",
                    required=True,
                    type=str,
                    help="The name of the knowledge graph")
parser.add_argument("--kg-path",
                    required=True,
                    help="The path to the knowledge graph file (.nt)")
parser.add_argument("--constraint-path",
                    required=True,
                    type=Path,
                    help="The path to the constraint file (.ttl)")
parser.add_argument("--ontology-path",
                    required=True,
                    type=Path,
                    help="The path to the ontology file (.ttl)")
parser.add_argument("--result-path",
                    required=True,
                    type=Path,
                    help="The path to the directory to store the results")
parser.add_argument("--kg-access-method",
                    choices=["memory", "memory-numerical", "hybrid", "sparql"],
                    default="mem",
                    help="The method used to access the knowledge graph")
parser.add_argument("--prefix",
                    type=str,
                    help="The most common prefix used in the knowledge graph for example 'http://example.com/'\nThis is only relevant if --kg-access-method is 'memory' since it has no effect on the other approaches")
parser.add_argument("--max-body-length",
                    type=int,
                    default=3,
                    help="Maximum number of atoms in a rule body")
parser.add_argument("--ontology-valid",
                    action="store_true",
                    help="Set this option if ontology is valid. This will skip the validation step")
parser.add_argument("--mine-neagitive-rules",
                    action="store_true",
                    help="Set this option if negative rules should be mined")

def create_graph(args) -> Graph:
    match args.kg_access_method:
        case "memory":

            pass
        case "memory-numerical":

            pass
        case "hybrid":
            pass
        case "sparql":
            pass

if __name__ == '__main__':
    args = parser.parse_args()
    startTime = time.time()
    graph = create_graph(args)
