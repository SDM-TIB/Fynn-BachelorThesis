import gc
import multiprocessing as mp
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from ExampleSampling import get_examples, get_negative_examples
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

def mine_rules(knowledge_graph: Graph, ontology: Ontology, set_size: int, max_depth: int, alpha: float,
               multiprocessing, workers, type_predicate:str='http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
               mine_negative=False) -> list[Rule]:
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
    if not g:
        print(f"There are no generation examples for {predicate}. No rule-mining possible.")
        return []
    if not v:
        print(f"There are no validation examples for {predicate}. No rule-mining possible.")
        return []
    print("Mining rules for", predicate)
    return mine_rules_for_target_predicate(g, v, predicate, knowledge_graph, type_predicate, ontology, max_depth, alpha, beta)

def mine_rules_for_target_predicate(g: set[tuple], v: set[tuple], predicate, knowledge_graph: Graph, type_predicate: str,
                                    ontology: Ontology, max_depth: int = 3, alpha: float = 0.5, beta: float = 0.5):
    r_out_dict = {}
    rule_dict = {}

    rule_weight_dict = {}
    r_out_cov_v_cardinality = [None]
    r_out_uncov_v = [None]

    paths = {Path((s, predicate, o), set()) for s, o in g}

    for path in paths:
        rule_dict_to_add = expand_path(path, knowledge_graph, ontology, type_predicate)
        for rule, new_paths in rule_dict_to_add.items():
            if rule in rule_dict:
                rule_dict[rule].update(new_paths)
            else:
                rule_dict[rule] = new_paths
    r_out_cov_g_set = set()
    r, min_weight = find_r(r_out_dict, r_out_cov_g_set, r_out_cov_v_cardinality, r_out_uncov_v, rule_dict,
                           rule_weight_dict, knowledge_graph, g, v, alpha, beta, max_depth)
    r_out_cov_g_set = set()

    while True:
        if not rule_dict or (len(r_out_cov_g_set) == len(g)) or min_weight >= 0:
            break

        if r.is_valid():
            r.set_time()
            r_out_dict[r] = rule_dict.pop(r)
            rule_weight_dict = {}
            r_out_cov_v_cardinality = [None]
            r_out_uncov_v = [None]
            print(f"FOUND RULE {r} with {min_weight}\n")

        else:
            if fits_max_depth(r, max_depth):
                expand_rule(r, rule_dict, knowledge_graph, ontology, type_predicate)
            rule_dict.pop(r)
        r, min_weight = find_r(r_out_dict, r_out_cov_g_set, r_out_cov_v_cardinality, r_out_uncov_v, rule_dict,
                               rule_weight_dict, knowledge_graph, g, v, alpha, beta, max_depth)

    return r_out_dict

def expand_rule(rule, rule_dict, knowledge_graph, ontology, type_predicate):
    if rule in rule_dict:
        paths = list(rule_dict[rule])
        for path in paths:
            rule_dict_to_add = expand_path(path, knowledge_graph, ontology, type_predicate)
            for rule, new_paths in rule_dict_to_add.items():
                if rule in rule_dict:
                    rule_dict[rule].update(new_paths)
                else:
                    rule_dict[rule] = new_paths

def find_r(R_out_dict:dict, r_out_cov_g_set: set, R_out_cov_v_cardinality:list, R_out_uncov_v:list, rule_dict:dict,
           rule_weight_dict:dict, knowledge_graph: Graph, g:set, v:set, alpha:float, beta:float, max_depth:int):
    min_weight = np.inf
    best_rule: Rule = None

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

    r_out_cov_g_set.update(cov_g(R_out, rule_dict, R_out_dict))

    beta_base_ratio = (cardinality_cov_r_out_v / cardinality_uncov_r_out_v) if cardinality_uncov_r_out_v else 0.0
    has_beta = (cardinality_cov_r_out_v != 0 and cardinality_uncov_r_out_v != 0)

    for rule in rule_dict.keys():
        if rule in rule_weight_dict:
            weight = rule_weight_dict[rule]
        else:
            weight = est_m_weight(rule, R_out_dict, rule_dict, knowledge_graph, alpha, beta, len_g, r_out_cov_g_set,
                                  uncov_r_out_v, v_remaining, cardinality_cov_r_out_v, has_beta, beta_base_ratio)
            rule_weight_dict[rule] = weight

        is_valid = rule.is_valid()
        if not fits_max_depth(rule, max_depth) and (weight >= 0 or not is_valid):
            rules_to_remove.add(rule)
            continue

        if weight < min_weight or (weight == min_weight and is_valid):
            best_rule = rule
            min_weight = weight

    for rule in rules_to_remove:
        rule_dict.pop(rule)

    return best_rule, min_weight

def fits_max_depth(r:Rule, max_depth):
    """Checks is a rule is below the maximum length"""
    return len(r.body) < max_depth

def expand_path(path: Path, knowledge_graph: Graph, ontology: Ontology, type_predicate: str):
    """Expands given path by one from frontiers, creates closed rules"""
    frontier = path.frontiers()

    if frontier is None:
        return {}

    path_body = path.body
    path_head = path.head
    nodes = path.get_nodes()
    rule_dict_to_add = {}
    triples: set[tuple] = set()
    entities_to_typecheck = set()
    for s, p, o in knowledge_graph.get_adjacent_triples(frontier):
        if p == type_predicate:
            continue

        triple = (s, p, o)
        if triple in path_body or triple == path_head:
            continue

        e = s if o == frontier else o

        if e != frontier and e in nodes:
            continue

        entities_to_typecheck.add(e)
        triples.add((triple, e))

    types = knowledge_graph.get_types_batched(entities_to_typecheck, type_predicate)
    for triple, e in triples:
        is_subject = (triple[0] == e)
        t: tuple = (types.get(e), None) if is_subject else (None, types.get(e))
        if ontology.fits_domain_range_known_types(triple, knowledge_graph, t, is_subject, not is_subject):
            new_path = path.copy()
            new_path.body.add(triple)
            rule = new_path.to_closed_rule(knowledge_graph.resolve_to_uri)

            if rule in rule_dict_to_add:
                rule_dict_to_add[rule].add(new_path)
            else:
                rule_dict_to_add[rule] = {new_path}
    return rule_dict_to_add