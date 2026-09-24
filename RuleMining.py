import gc
import multiprocessing as mp
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed, ThreadPoolExecutor
from ExampleSampling import get_examples, get_negative_examples
from KnowledgeGraph.SPARQLKG import SPARQLKG
from KnowledgeGraph.HybridKG import HybridKG
from KnowledgeGraph.Graph import Graph
from Ontology import Ontology
from Rule import Rule
from Path import Path
from WeightEstimation import cov_g, est_m_weight, rulelist_coverage, rulelist_unbound_coverage

_GLOBAL_KG: Graph = None
_GLOBAL_ONTOLOGY: Ontology = None

def init_state(kg, ontology):
    global _GLOBAL_KG, _GLOBAL_ONTOLOGY
    _GLOBAL_KG = kg
    _GLOBAL_ONTOLOGY = ontology

def mine_rules(knowledge_graph: Graph, ontology: Ontology, set_size: int, max_depth: int, alpha: float, multiprocessing, workers, type_predicate:str='http://www.w3.org/1999/02/22-rdf-syntax-ns#type', mine_negative=False) -> list[Rule]:
    if alpha > 1.0 or alpha < 0.0:
        raise ValueError("alpha must be in [0,1].")
    beta = 1 - alpha
    print(f"Computed beta as {beta}.\n")
    rules = []
    predicates = knowledge_graph.get_all_predicates()
    init_state(knowledge_graph, ontology)
    if multiprocessing:
        context = mp.get_context("fork")
        with ProcessPoolExecutor(mp_context=context, max_workers=workers) as executor:
            futures = [
                executor.submit(
                    process_batch_targets,
                    batch,
                    set_size,
                    type_predicate,
                    max_depth,
                    alpha,
                    beta,
                    mine_negative
                )
                for batch in knowledge_graph.get_balanced_predicate_batches() if batch
            ]

            for f in as_completed(futures):
                result = f.result()
                if result:
                    rules.extend(result)
                del result
            futures = None
            gc.collect()
    else:
        for predicate in predicates:
            rules.extend(process_target(predicate, set_size, type_predicate, max_depth, alpha, beta, mine_negative))

    return rules

def process_batch_targets(predicates, set_size, type_predicate, max_depth, alpha, beta, mine_negative):
    batch = []
    for predicate in predicates:
        batch.extend(process_target(predicate, set_size, type_predicate, max_depth, alpha, beta, mine_negative))
    return batch

def process_target(predicate, set_size, type_predicate, max_depth, alpha, beta, mine_negative):
    # print(f"creating input sets G and V for target predicate <{predicate}>...\n")
    knowledge_graph = _GLOBAL_KG
    ontology = _GLOBAL_ONTOLOGY
    edges = knowledge_graph.get_edges(predicate)
    if mine_negative:
        g = get_negative_examples(knowledge_graph, predicate, edges, ontology, set_size, type_predicate)
        v = get_examples(knowledge_graph, predicate, edges, set_size, ontology, type_predicate)
    else:
        g = get_examples(knowledge_graph, predicate, edges, set_size, ontology, type_predicate)
        v = get_negative_examples(knowledge_graph, predicate, edges, ontology, set_size, type_predicate)
    edges = []
    del edges
    # len_g = len(g)
    # if len_g < set_size
        # print(f"There aren't enough positive examples in the graph, proceeding with {len_g} examples.\n")

    # len_v = len(v)
    # if len_v < set_size:
        # print(f"There aren't enough negative examples in the graph, proceeding with {len_v} examples.\n")

    #TODO: Add warnings back
    if not g:
        # warnings.warn(f"There are no generation examples for . No rule-mining possible \n", UserWarning)
        return []
    if not v:
        # warnings.warn(f"There are no validation examples for . No rule-mining possible \n", UserWarning)
        return []

    # print(f"mining rules for target predicate <{predicate}>...\n")

    return mine_rules_for_target_predicate(g, v, predicate, knowledge_graph, type_predicate, ontology, max_depth, alpha, beta, mine_negative)

def mine_rules_for_target_predicate(g: set[tuple], v: set[tuple], predicate, knowledge_graph: Graph, type_predicate: str, ontology: Ontology, max_depth: int = 3, alpha: float = 0.5, beta: float = 0.5, mine_negative: bool = False):
    # TODO when expanding, excluding bad paths better?
    # TODO when finding r, mind rules with same weight, collect all and look through those until a rule is found
    r_out_dict = {}
    rule_dict = {}

    rule_weight_dict = {}
    r_out_cov_v_cardinality = [None]
    r_out_uncov_v = [None]

    paths = {Path((s, predicate, o), set()) for s, o in g}

    # TODO call expand rule here, duplicate code

    # if isinstance(knowledge_graph, SPARQLKG) or isinstance(knowledge_graph, HybridKG):
    #     with ThreadPoolExecutor() as executor:
    #         futures = [
    #             executor.submit(
    #                 expand_path_closed_rule,
    #                 path,
    #                 knowledge_graph,
    #                 ontology,
    #                 type_predicate
    #             )
    #             for path in paths
    #         ]
    #         for f in as_completed(futures):
    #             rule_dict_to_add = f.result()
    #             for rule, new_paths in rule_dict_to_add.items():
    #                 if rule in rule_dict:
    #                     rule_dict[rule].update(new_paths)
    #                 else:
    #                     rule_dict[rule] = new_paths
    # else:
    for path in paths:
        rule_dict_to_add = expand_path_closed_rule(path, knowledge_graph, ontology, type_predicate)
        for rule, new_paths in rule_dict_to_add.items():
            if rule in rule_dict:
                rule_dict[rule].update(new_paths)
            else:
                rule_dict[rule] = new_paths
    # Batched approach seems to only be faster for SPARQL and only if run as a single process possibly add as an option.
    # knowledge_graph.expand_paths(rule_dict, paths, ontology, type_predicate)

    r, min_weight = find_r(r_out_dict, r_out_cov_v_cardinality, r_out_uncov_v, rule_dict, rule_weight_dict, knowledge_graph, g, v, alpha, beta, max_depth)
    r_out_cov_g_set = set()

    while True:
        if not rule_dict or (len(r_out_cov_g_set) == len(g)) or min_weight >= 0:
            break

        if r.is_valid():
            r_out_dict[r] = rule_dict.pop(r)
            r_out_cov_g_set.update(cov_g(r, rule_dict, r_out_dict))
            rule_weight_dict = {}
            r_out_cov_v_cardinality = [None]
            r_out_uncov_v = [None]
            # print(f"\nFOUND RULE {r} with {min_weight}\n")

        else:
            if fits_max_depth_closed_rule(r, max_depth):
                expand_rule(r, rule_dict, knowledge_graph, ontology, type_predicate)
            rule_dict.pop(r)

        r, min_weight = find_r(r_out_dict, r_out_cov_v_cardinality, r_out_uncov_v, rule_dict, rule_weight_dict, knowledge_graph, g,
                               v, alpha, beta, max_depth)

    return r_out_dict

def expand_rule(rule, rule_dict, knowledge_graph, ontology, type_predicate):
    if rule in rule_dict:
        paths = list(rule_dict[rule])
        for path in paths:
            rule_dict_to_add = expand_path_closed_rule(path, knowledge_graph, ontology, type_predicate)
            for rule, new_paths in rule_dict_to_add.items():
                if rule in rule_dict:
                    rule_dict[rule].update(new_paths)
                else:
                    rule_dict[rule] = new_paths

def find_r(R_out_dict:dict, R_out_cov_v_cardinality:list, R_out_uncov_v:list, rule_dict:dict, rule_weight_dict:dict, knowledge_graph: Graph, g:set, v:set, alpha:float, beta:float, max_depth:int):

    min_weight = np.inf
    best_rule = None

    rules_to_remove = set()
    R_out = list(R_out_dict.keys())
    len_g = len(g)
    if R_out_cov_v_cardinality[0] is None:
        R_out_cov_v_cardinality[0] = len(rulelist_coverage(R_out, v, knowledge_graph))

    cardinality_cov_r_out_v = R_out_cov_v_cardinality[0]

    if R_out_uncov_v[0] is None:
        R_out_uncov_v[0] = rulelist_unbound_coverage(R_out, v, knowledge_graph)

    uncov_r_out_v = R_out_uncov_v[0]

    cardinality_uncov_r_out_v = len(uncov_r_out_v)

    v_remaining = v - uncov_r_out_v if uncov_r_out_v else v

    cov_g_R_out = cov_g(R_out, rule_dict, R_out_dict)

    beta_base_ratio = (cardinality_cov_r_out_v / cardinality_uncov_r_out_v) if cardinality_uncov_r_out_v else 0.0
    has_beta = (cardinality_cov_r_out_v != 0 and cardinality_uncov_r_out_v != 0)

    for rule in rule_dict.keys():
        if rule in rule_weight_dict:
            weight = rule_weight_dict[rule]
        else:
            weight = est_m_weight(rule, R_out_dict, rule_dict, knowledge_graph, alpha, beta, len_g, cov_g_R_out, uncov_r_out_v, v_remaining, cardinality_cov_r_out_v, has_beta, beta_base_ratio)
            rule_weight_dict[rule] = weight

        is_valid = rule.is_valid()
        if not fits_max_depth_closed_rule(rule, max_depth) and (weight >= 0 or not is_valid):
            rules_to_remove.add(rule)
            continue

        if weight < min_weight or (weight == min_weight and is_valid):
            best_rule = rule
            min_weight = weight

    for rule in rules_to_remove:
        rule_dict.pop(rule)

    return best_rule, min_weight

"""function for closed rules: states wether a rule is of allowed length"""
def fits_max_depth_closed_rule(r:Rule, max_depth):
    return len(r.body) < max_depth

"""Expands given path by one from frontiers, creates closed rules"""
def expand_path_closed_rule(path: Path, knowledge_graph: Graph, ontology: Ontology, type_predicate: str):
    frontier = path.frontiers_closed_rule()

    if frontier is None:
        # print(f"no frontier for {path}")
        return {}

    if knowledge_graph.is_literal(frontier):
        # Expansion option: Include literal comparisons as connection
        return {}

    path_body = path.body
    path_head = path.head
    nodes = path.get_nodes()
    rule_dict_to_add = {}
    for s, p, o in knowledge_graph.get_adjacent_triples(frontier):
        if p == type_predicate:
            continue

        triple = (s, p, o)
        if triple in path_body or triple == path_head:
            continue

        e = o if s == frontier else s

        if e != frontier and e in nodes:
            continue

        is_subject = (s == e)
        if ontology.fits_domain_range(triple, knowledge_graph, type_predicate, check_domain=is_subject, check_range=not is_subject):
            new_path = path.copy()
            new_path.body.add(triple)
            rule = new_path.to_rule_closed_rule(knowledge_graph.resolve_to_uri)

            if rule in rule_dict_to_add:
                rule_dict_to_add[rule].add(new_path)
            else:
                rule_dict_to_add[rule] = {new_path}
    return rule_dict_to_add