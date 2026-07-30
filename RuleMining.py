from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from ExampleSampling import get_examples, get_negative_examples
from KnowledgeGraph.Graph import Graph
from Ontology import Ontology
from Rule import Rule
from Path import Path
from Utility import est_m_weight, cov_g

_GLOBAL_KG = None
_GLOBAL_ONTOLOGY = None

def init_worker(kg, ontology):
    global _GLOBAL_KG, _GLOBAL_ONTOLOGY
    _GLOBAL_KG = kg
    _GLOBAL_ONTOLOGY = ontology

def mine_rules(knowledge_graph: Graph, ontology: Ontology, set_size: int, max_depth: int, alpha: float, type_predicate:str='http://www.w3.org/1999/02/22-rdf-syntax-ns#type', mine_negative=False) -> list[Rule]:
    if alpha > 1.0 or alpha < 0.0:
        raise ValueError("alpha must be in [0,1].")
    beta = 1 - alpha
    print(f"Computed beta as {beta}.\n")
    init_worker(knowledge_graph, ontology)
    expand_fun = expand_path_closed_rule
    fits_max_depth = fits_max_depth_closed_rule

    rules = []

    # with ProcessPoolExecutor() as executor:
    #     futures = [
    #         executor.submit(
    #             process_target,
    #             predicate,
    #             set_size,
    #             _GLOBAL_KG,
    #             _GLOBAL_ONTOLOGY,
    #             type_predicate,
    #             expand_fun,
    #             fits_max_depth,
    #             max_depth,
    #             alpha,
    #             beta,
    #             mine_negative
    #         )
    #         for predicate in knowledge_graph.get_all_predicates()
    #     ]
    #
    #     for f in as_completed(futures):
    #         result = f.result()
    #         if result:
    #             rules.extend(result)

    for predicate in knowledge_graph.get_all_predicates():
        rules.extend(process_target(predicate, set_size, knowledge_graph, ontology, type_predicate, expand_fun, fits_max_depth, max_depth, alpha, beta, mine_negative))

    return rules

def process_target(predicate, set_size, knowledge_graph, ontology, type_predicate, expand_fun, fits_max_depth, max_depth, alpha, beta, mine_negative):
    print(f"creating input sets G and V for target predicate <{predicate}>...\n")

    g = get_examples(knowledge_graph, predicate, set_size, ontology, type_predicate)
    len_g = len(g)
    if len_g < set_size:
        print(f"There aren't enough positive examples in the graph, proceeding with {len_g} examples.\n")

    v = get_negative_examples(knowledge_graph, predicate, ontology, set_size, type_predicate)

    len_v = len(v)
    if len_v < set_size:
        print(f"There aren't enough negative examples in the graph, proceeding with {len_v} examples.\n")

    #TODO: Add warnings back
    if not g:
        # warnings.warn(f"There are no generation examples for . No rule-mining possible \n", UserWarning)
        return []
    if not v:
        # warnings.warn(f"There are no validation examples for . No rule-mining possible \n", UserWarning)
        return []

    print(f"mining rules for target predicate <{predicate}>...\n")

    return mine_rules_for_target_predicate(g, v, predicate, knowledge_graph, type_predicate, ontology, expand_fun,
                                           fits_max_depth, max_depth, alpha, beta, mine_negative)

def mine_rules_for_target_predicate(g: set[tuple], v: set[tuple], predicate, knowledge_graph: Graph, type_predicate: str, ontology: Ontology, expand_fun, fits_max_depth, max_depth: int = 3, alpha: float = 0.5, beta: float = 0.5, mine_negative: bool = False):
    # TODO when expanding, excluding bad paths better?
    # TODO when finding r, mind rules with same weight, collect all and look through those until a rule is found

    r_out_dict = {}
    rule_dict = {}

    rule_weight_dict = {}
    r_out_cov_v_cardinality = [None]
    r_out_uncov_v = None

    paths = {Path((s, predicate, o), set()) for s, o in g}

    # TODO call expand rule here, duplicate code

    for path in paths:
        expand_fun(rule_dict, path, knowledge_graph, ontology, type_predicate)

    r, min_weight = find_r(r_out_dict, r_out_cov_v_cardinality, r_out_uncov_v, rule_dict, rule_weight_dict, knowledge_graph, g, v,
                           alpha, beta, fits_max_depth, max_depth)

    passes = 0
    while True:

        if not rule_dict or len(cov_g(list(r_out_dict.keys()), rule_dict, r_out_dict)) / len(g) == 1 or min_weight >= 0:
            break

        if r.is_valid():
            r_out_dict[r] = rule_dict.pop(r)

            rule_weight_dict = {}
            r_out_cov_v_cardinality = [None]
            r_out_uncov_v = None
            print(f"\n\nFOUND RULE {r} with {min_weight}\n\n")

        else:
            if fits_max_depth(r, max_depth):
                expand_rule(r, rule_dict, knowledge_graph, ontology, type_predicate, expand_fun)
            rule_dict.pop(r)

        r, min_weight = find_r(r_out_dict, r_out_cov_v_cardinality, r_out_uncov_v, rule_dict, rule_weight_dict, knowledge_graph, g,
                               v, alpha, beta, fits_max_depth, max_depth)
        print(passes)
        passes += 1

    return r_out_dict

def expand_rule(rule, rule_dict, knowledge_graph, ontology, type_predicate, expand_fun):
    if rule in rule_dict:
        paths = list(rule_dict[rule])
        for path in paths:
            expand_fun(rule_dict, path, knowledge_graph, ontology, type_predicate)

def find_r(R_out_dict:dict, R_out_cov_v_cardinality:list, R_out_uncov_v:set, rule_dict:dict, rule_weight_dict:dict, knowledge_graph: Graph, g:set, v:set, alpha:float, beta:float, fits_max_depth, max_depth:int):

    min_weight = np.inf
    r = None

    rules_to_remove = set()

    for rule in rule_dict.keys():
        if rule in rule_weight_dict:
            weight = rule_weight_dict[rule]
        else:
            weight = est_m_weight(rule, R_out_dict, rule_dict, knowledge_graph, g, v, alpha, beta, R_out_cov_v_cardinality, R_out_uncov_v)
            rule_weight_dict[rule] = weight

        if not fits_max_depth(rule, max_depth) and (weight >= 0 or not rule.is_valid()):
            rules_to_remove.add(rule)
            continue

        if weight < min_weight or (weight == min_weight and rule.is_valid()):
            r = rule
            min_weight = weight

    for rule in rules_to_remove:
        rule_dict.pop(rule)

    return r, min_weight

"""function for closed rules: states wether a rule is of allowed length"""
def fits_max_depth_closed_rule(r:Rule, max_depth):
    return len(r.body) < max_depth


"""Expands given path by one from frontiers, creates closed rules"""
def expand_path_closed_rule(rule_dict: dict, path: Path, knowledge_graph: Graph, ontology: Ontology, type_predicate: str):

    frontier = path.frontiers_closed_rule()

    if frontier is None:
        print(f"no frontier for {path}")
        return

    if knowledge_graph.is_literal(frontier):
        # TODO include literal comparisons as connection
        return

    predicates = knowledge_graph.get_predicates(frontier)

    for p in predicates:
        if p == type_predicate:
            continue


        for pair in knowledge_graph.get_edges(p):
            if frontier not in pair:
                continue

            triple = (pair[0], p, pair[1])
            if triple in path.body or triple == path.head:
                continue

            e = pair[0] if pair[1] == frontier else pair[1]

            if e != frontier and e in path.get_nodes():
                continue

            is_subject = (pair[0] == e)
            if ontology.fits_domain_range(triple, knowledge_graph, type_predicate, check_domain=is_subject, check_range=not is_subject):
                new_path = path.copy()
                new_path.body.add(triple)
                rule = new_path.to_rule_closed_rule()

                if rule in rule_dict:
                    rule_dict[rule].add(new_path)
                else:
                    rule_dict[rule] = {new_path}
    return