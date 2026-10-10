from typing import Any

from KnowledgeGraph import Graph
from Rule import Rule

def cov_g(rules: Any, rule_dict: dict[Any, set[Any]], r_out_dict: dict[Any, Any]) -> set[tuple]:
    """
    Calculates the coverage of a rule or a list of rules on the generation set.
    """
    c = set()
    if not rules:
        return c
    if isinstance(rules, Rule):
        if rules in rule_dict:
            for path in rule_dict[rules]:
                c.add((path.head[0], path.head[2]))
        elif rules in r_out_dict:
            for path in r_out_dict[rules]:
                c.add((path.head[0], path.head[2]))
        else:
            raise ValueError("unknown rule")
    elif isinstance(rules, list) and rules and isinstance(rules[0], Rule):
        for rule in rules:
            c.update(cov_g(rule, rule_dict, r_out_dict))
    else:
        raise ValueError("r must be type Rule or list[Rule]")

    return c

"""helper function to rulelist_coverage and rulelist_unbound_coverage"""
def rulelist_call_coverage(r: Rule, v: set[tuple], knowledge_graph: Graph, out: set):
    for example_pair in v:
        if example_pair in out:
            continue
        if covers_example(r, example_pair, knowledge_graph):
            out.add(example_pair)


def rulelist_coverage(rules: list[Rule], v: set[tuple], knowledge_graph: Graph) -> set[tuple]:
    out = set()
    for rule in rules:
        rulelist_call_coverage(rule, v, knowledge_graph, out)
    return out


def rulelist_unbound_coverage(rules: list[Rule], examples: set[tuple], knowledge_graph: Graph) -> set[tuple]:
    out = set()
    for rule in rules:
        rulelist_call_coverage(rule.get_unbound(), examples, knowledge_graph, out)
    return out


def unbound_coverage(rule: Rule, examples: set[tuple], knowledge_graph: Graph) -> set[tuple]:
    out = set()
    unbound = rule.get_unbound()
    for example_pair in examples:
        if covers_example(unbound, example_pair, knowledge_graph):
            out.add(example_pair)
    return out

def covers_example(rule: Rule, example: tuple, kg: Graph) -> bool:
    """Checks if a rule covers a given example pair."""
    s_val, o_val = example
    name_dict = {rule.head[0]: s_val}
    if rule.head[2] in name_dict:
        if name_dict[rule.head[2]] != o_val:
            return False
    else:
        name_dict[rule.head[2]] = o_val

    return kg.patterns_in_graph(rule.body, name_dict)

"""estimated marginal weight"""
def est_m_weight(rule: Rule, R_out_dict, rule_dict, knowledge_graph: Graph, alpha: float, beta: float,
                 len_g: int, cov_g_R_out: set, uncov_r_out_v: set, v_remaining: set, cardinality_cov_r_out_v: int,
                 has_beta: bool, beta_base_ratio: float):
    new_cov = len(cov_g(rule, rule_dict, R_out_dict) - cov_g_R_out)
    alpha_term = -alpha * (new_cov / len_g)

    if not has_beta:
        return alpha_term

    uncov_r_v = unbound_coverage(rule, v_remaining, knowledge_graph)
    cardinality_uncov_r_out_r_v = len(uncov_r_out_v | uncov_r_v)

    if cardinality_uncov_r_out_r_v == 0:
        return alpha_term - beta * beta_base_ratio

    return alpha_term + beta * ((cardinality_cov_r_out_v / cardinality_uncov_r_out_r_v) - beta_base_ratio)