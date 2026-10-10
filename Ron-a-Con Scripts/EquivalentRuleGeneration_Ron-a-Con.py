# import argparse
# import ast
# import json
# from rdflib import Graph
# import os
# import time
# from pathlib import Path
# from Normalization.Validation import travshacl
# from Normalization.Normalization_transform import transform
# from RuleMining.Rule_mining import mine_rules, mine_rules_for_target_predicate, expand_path_rudik, fits_max_depth_rudik
# from RuleMining.Util import parseGraph, parseOntology, new_preds, neg_preds, check_preds_in_graph
# from RuleMining.Classes import IncidenceList, Ontology, P_map
# from main import initialize, delete_existing_result
#
# parser = argparse.ArgumentParser(description='')
#
# parser.add_argument("--generation-set",
#                     type=ast.literal_eval)
# parser.add_argument("--validation-set",
#                     type=ast.literal_eval)
# parser.add_argument("--predicate")
# parser.add_argument("--dataset",
#                     type=Path)
#
# def get_connecting_predicates(graph: IncidenceList, s, o):
#     return { predicate for predicate, pairs in graph.edges.items() if (s, o) in pairs }
#
# if __name__ == "__main__":
#     try:
#         arguments = parser.parse_args()
#         #MAX check cwd
#         cwd = os.getcwd()
#         if (os.path.basename(cwd) != 'src'):
#             raise RuntimeError(f"Expected working directory to be the projects 'src' folder, but got {cwd}")
#
#         start_time = time.time()
#         print("Starting symbolic prediction generation...")
#
#         # Initialize configuration
#         input_config = './Data/input.json'
#
#         #Initializaing from the input.json file
#         (prefix, rules_path, rdf_path, kg_path, ontology_path, predictions_folder, constraints_folder, kg_name, max_depth,
#          set_size, type_predicate, alpha, negative_rules, onto_valid) = initialize(input_config)
#         result_path = f'{constraints_folder}/result_{kg_name}'
#         delete_existing_result(result_path)
#         g = Graph()
#         g.parse(rdf_path, format='nt')
#
#
#         # Validate SHACL constraints
#         print("\nValidating results...")
#         val_results = travshacl(g, constraints_folder, kg_name)
#
#         # Normalizing enriched KG (enrichedKG obtained from symbolic predictions)
#         print("\nTransforming results...")
#         transformed_kg, transform_output_dir, original_predicates = transform(g,constraints_folder, prefix, kg_name)
#
#         time_start_parse = time.time()
#         kg_transformed_i_list = IncidenceList()
#         parseGraph(f"{transform_output_dir}/TransformedKG_{kg_name}.nt", kg_transformed_i_list, prefix)
#         ontology = Ontology()
#         parseOntology(ontology_path, ontology, prefix)
#
#         with open(f"{transform_output_dir}/predicate_mappings.json", "r", encoding="utf-8") as p_map_file:
#             predicate_mappings = json.load(p_map_file)
#         with open(f"{transform_output_dir}/no_predicate_mappings.json", "r", encoding="utf-8") as np_map_file:
#             neg_predicate_mappings = json.load(np_map_file)
#         check_preds_in_graph(neg_predicate_mappings, transformed_kg)
#         expand_fun = expand_path_rudik
#         fits_max_depth = fits_max_depth_rudik
#         if not arguments.dataset:
#             predicate = arguments.predicate
#             pmap = P_map(predicate, new_preds(predicate, predicate_mappings), set(), predicate_mappings, neg_predicate_mappings)
#             pmap.neg_predicates = neg_preds(pmap.predicates, neg_predicate_mappings)
#             generation = set()
#             validation = set()
#             p = None
#             for (s, o) in arguments.generation_set:
#                 for transformed_p in get_connecting_predicates(kg_transformed_i_list, s, o):
#                     if transformed_p.startswith(f"{predicate}_"):
#                         p = transformed_p
#                         break
#                 if not p:
#                     raise ValueError("No predicate found")
#                 generation.add((s, p, o))
#             for (s, o) in arguments.validation_set:
#                 validation.add((s, o))
#
#             rules = mine_rules_for_target_predicate(generation, validation, pmap, kg_transformed_i_list, type_predicate,
#                                                     ontology, expand_fun, fits_max_depth, negative_rules, max_depth=max_depth)
#             for rule in rules:
#                 print(rule)
#             exit(0)
#
#         with arguments.dataset.open("r") as file:
#             dataset = json.load(file)
#         rules = []
#         for entry in dataset:
#             predicate = entry["predicate"]
#             print("Mining rules for", predicate)
#             generation_set = {tuple(pair) for pair in entry["generation_set"]}
#             validation_set = {tuple(pair) for pair in entry["validation_set"]}
#             pmap = P_map(predicate, new_preds(predicate, predicate_mappings), set(), predicate_mappings,
#                          neg_predicate_mappings)
#             pmap.neg_predicates = neg_preds(pmap.predicates, neg_predicate_mappings)
#             generation = set()
#             validation = set()
#             for (s, o) in generation_set:
#                 p = None
#                 for transformed_p in get_connecting_predicates(kg_transformed_i_list, s, o):
#                     if transformed_p.startswith(f"{predicate}_"):
#                         p = transformed_p
#                         break
#                 if not p:
#                     raise ValueError("No predicate found")
#                 generation.add((s, p, o))
#             for (s, o) in validation_set:
#                 validation.add((s, o))
#             rules.extend(mine_rules_for_target_predicate(generation, validation, pmap, kg_transformed_i_list, type_predicate,
#                                                     ontology, expand_fun, fits_max_depth, negative_rules, max_depth=max_depth))
#
#         for rule in rules:
#             print(rule)
#     except Exception as e:
#         error_msg = f"Error occurred during execution: {str(e)}"
#         print(f"\n{error_msg}")
#         if 'logger' in locals():
#             pass
#         raise