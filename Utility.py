from typing import Any, Optional
from KnowledgeGraph.Graph import Graph
from Rule import Rule

def clean_uri(uri: str, prefix: Optional[str] = None) -> str:
    """Removes RDF formatting syntax (<>, spaces) and optionally strips prefixes."""
    token = uri.strip("<> \n\r\t")
    if prefix and token.startswith(prefix):
        return token[len(prefix) :]
    return token

def cov_g(rules: Any, rule_dict: dict[Any, set[Any]], r_out_dict: dict[Any, Any]) -> set[tuple]:
    """
    Calculates the coverage of a rule or a list of rules on the generation set.
    """
    if not isinstance(rules, list):
        rules = [rules]
    coverage = set()
    for rule in rules:
        if rule in rule_dict:
            paths = rule_dict[rule]
        elif rule in r_out_dict:
            paths = r_out_dict[rule]
        else:
            continue
        for path in paths:
            coverage.add((path.head[0], path.head[2]))
    return coverage

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
def est_m_weight(r: Rule, R_out_dict, rule_dict, knowledge_graph: Graph, g: set, v: set, alpha: float, beta: float, R_out_cov_v_cardinality: list, R_out_uncov_v: set):
    R_out = list(R_out_dict.keys())

    if R_out_cov_v_cardinality[0] == None:
        cardinality_cov_r_out_v = len(rulelist_coverage(R_out, v, knowledge_graph))
        R_out_cov_v_cardinality[0] = cardinality_cov_r_out_v
        test = True
    else:
        cardinality_cov_r_out_v = R_out_cov_v_cardinality[0]

    if R_out_uncov_v == None:
        uncov_r_out_v = rulelist_unbound_coverage(R_out, v, knowledge_graph)

        R_out_uncov_v = uncov_r_out_v
    else:
        uncov_r_out_v = R_out_uncov_v

    cardinality_uncov_r_out_v = len(uncov_r_out_v)

    # no need to check for the examples already in uncov_r_out_v (--> (v - uncov_r_out_v)),  since uncov_r_v is only used in union
    uncov_r_v = unbound_coverage(r, (v - uncov_r_out_v), knowledge_graph)
    cardinality_uncov_r_out_r_v = len(set.union(uncov_r_out_v, uncov_r_v))

    if not cardinality_cov_r_out_v or not cardinality_uncov_r_out_v:
        # if this is zero we know the beta part is zero, the divisors will also be zero resulting in error, thus removing beta part altogether
        return -alpha * ((len(cov_g(r, rule_dict, R_out_dict) - cov_g(R_out, rule_dict, R_out_dict))) / len(g))

    if not cardinality_uncov_r_out_r_v:
        # if this is zero there is division by zero in first fraction of beta part, setting it to zero
        return -alpha * (
                    (len(cov_g(r, rule_dict, R_out_dict) - cov_g(R_out, rule_dict, R_out_dict))) / len(g)) - beta * (
                    cardinality_cov_r_out_v / cardinality_uncov_r_out_v)

    return -alpha * ((len(cov_g(r, rule_dict, R_out_dict) - cov_g(R_out, rule_dict, R_out_dict))) / len(g)) + beta * (
                (cardinality_cov_r_out_v / cardinality_uncov_r_out_r_v) - (
                    cardinality_cov_r_out_v / cardinality_uncov_r_out_v))


"""checks wether a triple represents a valid literal comparison."""
def is_valid_comp(triple):
    if not is_literal_comp(triple[1]) or (literal_type(triple[0]) != literal_type(triple[2])):
        return False

    if triple[1] == "=":
        if triple[0] != triple[2]:
            return False
    elif triple[1] == "<":
        if triple[0] >= triple[2]:
            return False

    return True

"""help function for fits_domain_range(), extracts an xsd-type from a string"""
def literal_type(l: str):
    temp = l.split("\"")[2]
    if temp:
        if temp.__contains__("<"):
            # with uri
            split = temp.split("/")
            return split[len(split) - 1].removesuffix(">")
        else:
            if temp.__contains__(":"):
                # with prefix abbreviation
                return temp.split(":")[1]

    # no xsd type given
    return "anyType"

"""checks if predicate is a literal comparison"""
def is_literal_comp(p):
    if p == "=" or p=="<":
        return True
    return False
