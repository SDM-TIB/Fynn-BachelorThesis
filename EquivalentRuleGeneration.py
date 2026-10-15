import argparse
import ast
import json
import time
from pathlib import Path
from KnowledgeGraph import SPARQLKG, NumericalKG, MemoryKG, Graph
from KnowledgeGraph.HybridKG import HybridKG
from NegativeExampleGeneration import generate_negative_triples
from Ontology import parse_ontology
from RuleMining import mine_rules_for_target_predicate
from Validation import shacl_validation

parser = argparse.ArgumentParser(description="Mines rules using the provided predicate(s) generation and validation set(s).")

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
                    default="memory",
                    help="The method used to access the knowledge graph")
parser.add_argument("--prefix",
                    type=str,
                    help="The most common prefix used in the knowledge graph for example 'http://example.com/'")
parser.add_argument("--max-body-length",
                    type=int,
                    default=3,
                    help="Maximum number of atoms in a rule body")
parser.add_argument("--generation-set",
                    type=ast.literal_eval)
parser.add_argument("--validation-set",
                    type=ast.literal_eval)
parser.add_argument("--predicate")
parser.add_argument("--dataset",
                    type=Path)


def create_graph() -> Graph:
    match arguments.kg_access_method:
        case "memory":
            return MemoryKG(arguments.kg_path, arguments.prefix)
        case "memory-numerical":
            return NumericalKG(arguments.kg_path, arguments.prefix)
        case "hybrid":
            return HybridKG(arguments.sparql_access_url, arguments.prefix, False, 0)
        case "sparql":
            return SPARQLKG(arguments.sparql_access_url, arguments.prefix, False, 0)
    raise ValueError("Invalid argument for --kg-access-method")

def parse_predicate(predicate, generation_set, validation_set):
    if isinstance(graph, MemoryKG):
        new_predicate = predicate
        g = {(s, o) for (s, o) in generation_set}
        v = {(s, o) for (s, o) in validation_set}
    elif isinstance(graph, NumericalKG):
        new_predicate = mapping_str_id[predicate]
        g = {(mapping_str_id[s], mapping_str_id[o]) for (s, o) in generation_set}
        v = {(mapping_str_id[s], mapping_str_id[o]) for (s, o) in validation_set}
    else:
        new_predicate = f"{predicate}"
        g = {(f"{s}", f"{o}") for (s, o) in generation_set}
        v = {(f"{s}", f"{o}") for (s, o) in validation_set}

    return new_predicate, g, v

if __name__ == '__main__':
    arguments = parser.parse_args()
    start_time = time.time()
    validation_result_dir = arguments.result_path / "validation_results"
    validation_result_dir.mkdir(exist_ok=True)
    shacl_validation(arguments.kg_access_method, arguments.constraint_path.parent, arguments.kg_path,
                     arguments.sparql_access_url, validation_result_dir)

    graph = create_graph()

    # Negative Example Generation
    validation_report_path = validation_result_dir / "validationReport.ttl"
    negative_triples = generate_negative_triples(graph, validation_report_path, arguments.constraint_path)
    graph.add_negative_triples(negative_triples)
    del negative_triples
    ontology = parse_ontology(arguments.ontology_path)
    if isinstance(graph, NumericalKG):
        mapping_str_id = graph.mapping_str_id.copy()

    graph.freeze(multiprocess=False, workers=0)
    rule_mining_start_time = time.time()
    # Single Predicate Rule Mining
    if not arguments.dataset:
        predicate, g, v = parse_predicate(arguments.predicate, arguments.generation_set, arguments.validation_set)
        rules = mine_rules_for_target_predicate(g, v, predicate, graph, type_predicate='http://www.w3.org/1999/02/22-rdf-syntax-ns#type', ontology=ontology, max_depth=arguments.max_body_length)
        for rule in rules:
            print(rule)
        exit(0)

    # Dataset Rule Mining
    with arguments.dataset.open("r") as file:
        dataset = json.load(file)
    rules = []
    for entry in dataset:
        predicate = entry["predicate"]
        generation = { tuple(pair) for pair in entry["generation_set"] }
        validation = { tuple(pair) for pair in entry["validation_set"] }
        p, g, v = parse_predicate(predicate, generation, validation)
        rules.extend(mine_rules_for_target_predicate(g, v, p, graph, type_predicate='http://www.w3.org/1999/02/22-rdf-syntax-ns#type', ontology=ontology, max_depth=arguments.max_body_length))

    print("Mined " + str(len(rules)) + " rules in " + str(time.time() - start_time) + " seconds (" + str(time.time() - rule_mining_start_time) + ")")
    for rule in rules:
        print(rule)