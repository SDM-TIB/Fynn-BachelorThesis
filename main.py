import argparse
import time

from KnowledgeGraph import NumericalKG
from KnowledgeGraph.Graph import Graph
from pathlib import Path
from KnowledgeGraph.SPARQLKG import SPARQLKG
from Ontology import parse_ontology
from Rule import get_as_tsv
from RuleMining import mine_rules
from NegativeExampleGeneration import generate_negative_triples
from KnowledgeGraph.MemoryKG import MemoryKG
from Validation import shacl_validation

parser = argparse.ArgumentParser(description="")

parser.add_argument("--kg-name",
                    required=True,
                    type=str,
                    help="The name of the knowledge graph")
parser.add_argument("--kg-path",
                    help="The path to the knowledge graph file (.nt). This is required if --kg-access-method is 'memory' or 'memory-numerical'.")
parser.add_argument("--sparql-access-url",
                    type=str,
                    help="The URL to the SPARQL endpoint to access the knowledge graph. This is required if --kg-access-method is 'hybrid' or 'SPARQL'.")
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
                    default="memory-numerical",
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
parser.add_argument("--example-set-size",
                    type=int,
                    default=20,
                    help="The size of the example set used during rule mining")
parser.add_argument("--overwrite",
                    action="store_true",
                    help="Set this option to overwrite existing files.")
parser.add_argument("--write-output",
                    action="store_true",
                    help="Set this option to write the results to a file in --result_path")
parser.add_argument("--multiprocess",
                    action="store_true",
                    help="Set this option if you want to use multiprocessing")
parser.add_argument("--mine-negative-rules",
                    action="store_true",
                    help="Set this option if negative rules should be mined")

def create_graph(arguments) -> Graph:
    match arguments.kg_access_method:
        case "memory":
            return MemoryKG(arguments.kg_path, arguments.prefix)
        case "memory-numerical":
            return NumericalKG(arguments.kg_path, arguments.prefix)
        case "hybrid":
            return None
        case "sparql":
            return SPARQLKG(arguments.sparql_access_url)
    raise ValueError("Invalid argument for --kg-access-method")

if __name__ == '__main__':
    arguments = parser.parse_args()
    start_time = time.time()
    graph = create_graph(arguments)
    print("Graph created in: ", time.time() - start_time)

    # SHACL validation
    start_validation = time.time()
    validation_result_dir = arguments.result_path / "validation_results"
    validation_result_dir.mkdir(exist_ok=True)
    shacl_validation(arguments.kg_access_method, arguments.constraint_path.parent, arguments.kg_path, arguments.sparql_access_url, validation_result_dir)
    print("SHACL validation took: ", time.time() - start_validation)

    # Negative Example Generation
    negative_example_generation_start_time = time.time()
    validation_report_path = validation_result_dir / "validationReport.ttl"
    negative_triples = generate_negative_triples(graph, validation_report_path, arguments.constraint_path)
    print(f"Generated {len(negative_triples)} negative triples in: ", time.time() - negative_example_generation_start_time)
    graph.add_negative_triples(negative_triples)

    # Ontology parsing
    ontology = parse_ontology(arguments.ontology_path, arguments.prefix)

    rules = mine_rules(knowledge_graph=graph, ontology=ontology, set_size=arguments.example_set_size, max_depth=arguments.max_body_length, alpha=0.5, multiprocessing=arguments.multiprocess, mine_negative=arguments.mine_negative_rules)

    print("Total time: ", time.time() - start_time)

    for rule in rules:
        print(rule)
    if arguments.write_output:
        with open(arguments.result_path / f"{arguments.kg_name}.tsv", mode='w', newline='', encoding='utf-8') as file:
            file.write(get_as_tsv(rules, graph.resolve_to_uri))