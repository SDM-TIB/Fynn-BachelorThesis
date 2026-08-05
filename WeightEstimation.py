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
def rulelist_call_coverage(r: Rule, v: set[tuple], knowledge_graph: Graph, out: set, bound: bool = True):
    for example_pair in v:
        if example_pair in out:
            continue
        if covers_example(r, example_pair, knowledge_graph, bound=bound):
            out.add(example_pair)


def rulelist_coverage(rules: list[Rule], v: set[tuple], knowledge_graph: Graph) -> set[tuple]:
    out = set()
    for rule in rules:
        rulelist_call_coverage(rule, v, knowledge_graph, out)
    return out


def rulelist_unbound_coverage(rules: list[Rule], examples: set[tuple], knowledge_graph: Graph) -> set[tuple]:
    out = set()
    for rule in rules:
        rulelist_call_coverage(rule, examples, knowledge_graph, out, bound=False)
    return out


def unbound_coverage(rule: Rule, examples: set[tuple], knowledge_graph: Graph) -> set[tuple]:
    out = set()
    for example_pair in examples:
        if covers_example(rule, example_pair, knowledge_graph, bound=False):
            out.add(example_pair)
    return out


def covers_example(rule: Rule, example: tuple, kg: Graph, bound: bool = True) -> bool:
    """Checks if a rule covers a given example pair."""
    s_val, o_val = example
    name_dict = {rule.head[0]: s_val}
    if bound:
        if rule.head[2] in name_dict:
            if name_dict[rule.head[2]] != o_val:
                return False
        else:
            name_dict[rule.head[2]] = o_val

    return _patterns_in_graph(rule.body, name_dict, kg)


def _patterns_in_graph(body: set[tuple], name_dict: dict, kg: Graph) -> bool:
    """Helper function to check if triple patterns are instantiable in KG."""
    if not body:
        return True

    solutions = [name_dict]
    handled_patterns = set()

    while len(handled_patterns) < len(body):
        best_pattern = None
        for pattern in body:
            if pattern in handled_patterns:
                continue
            if pattern[0] in solutions[0] and pattern[2] in solutions[0]:
                best_pattern = pattern
                break

        if best_pattern:
            s_var, p, o_var = best_pattern
            new_solutions = []
            for sol in solutions:
                if bool(kg.get_triples(subject=sol[s_var], predicate=p, object=sol[o_var])):
                    new_solutions.append(sol)
            solutions = new_solutions
            handled_patterns.add(best_pattern)
        else:
            for pattern in body:
                if pattern in handled_patterns:
                    continue
                if pattern[0] in solutions[0] or pattern[2] in solutions[0]:
                    best_pattern = pattern
                    break

            if not best_pattern:
                for pattern in body:
                    if pattern not in handled_patterns:
                        best_pattern = pattern
                        break

            if best_pattern:
                s_var, p, o_var = best_pattern
                new_solutions = []
                for sol in solutions:
                    s_bound = sol.get(s_var)
                    o_bound = sol.get(o_var)

                    matches = kg.get_triples(subject=s_bound, predicate=p, object=o_bound)
                    for m_s, m_p, m_o in matches:
                        new_sol = sol.copy()
                        new_sol[s_var] = m_s
                        new_sol[o_var] = m_o
                        new_solutions.append(new_sol)
                solutions = new_solutions
                handled_patterns.add(best_pattern)

        if not solutions:
            return False

    return True


"""estimated marginal weight"""
def est_m_weight(rule: Rule, R_out_dict, rule_dict, knowledge_graph: Graph, alpha: float, beta: float, len_g: int, cov_g_R_out: set, uncov_r_out_v: set, v_remaining: set, cardinality_cov_r_out_v: int, has_beta: bool, beta_base_ratio: float):
    new_cov = len(cov_g(rule, rule_dict, R_out_dict) - cov_g_R_out)
    alpha_term = -alpha * (new_cov / len_g)

    if not has_beta:
        return alpha_term

    uncov_r_v = unbound_coverage(rule, v_remaining, knowledge_graph)
    cardinality_uncov_r_out_r_v = len(uncov_r_out_v | uncov_r_v)

    if cardinality_uncov_r_out_r_v == 0:
        return alpha_term - beta * beta_base_ratio

    return alpha_term + beta * ((cardinality_cov_r_out_v / cardinality_uncov_r_out_r_v) - beta_base_ratio)