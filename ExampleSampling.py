import random

from KnowledgeGraph.Graph import Graph
from Ontology import Ontology


def get_examples(knowledge_graph: Graph, predicate, set_size, ontology: Ontology, type_predicate) -> set[tuple]:
    examples = set()

    edges = knowledge_graph.get_edges(predicate)
    for subject, object in edges:
        pair = (subject, object)
        triple = (subject, predicate, object)
        if ontology.fits_domain_range(triple, knowledge_graph, type_predicate):
            examples.add(pair)
            if len(examples) >= set_size:
                break
    return examples

def get_negative_examples(knowledge_graph: Graph, predicate, ontology: Ontology, set_size: int, type_predicate: str) -> set[tuple]:
    examples = set()

    edges = knowledge_graph.get_negative_edges(predicate)

    for pair in edges:
        examples.add(pair)
        if len(examples) >= set_size:
            return examples

    if len(examples) < set_size:
        print(f"{len(examples)} examples found from constraint violations, selecting remaining {set_size - len(examples)} examples from graph.\n")
        examples.update(get_LCWA_negative_examples(knowledge_graph, predicate, ontology, set_size - len(examples), type_predicate))

    if len(examples) < set_size:
        print(f"There aren't enough negative examples in the graph, choosing {set_size - len(examples)} random examples.\n")
        examples.update(get_random_negative_examples(knowledge_graph, predicate, set_size - len(examples), examples))

    return examples

def get_LCWA_negative_examples(knowledge_graph, predicate, ontology, count: int, type_predicate, max_attempts=None) -> set[tuple]:
    out = set()

    forbidden_edges = set()
    subjects = set()
    objects = set()
    edges = knowledge_graph.get_edges(predicate)
    if not edges:
        return out
    if not max_attempts:
        max_attempts = count * 10
    forbidden_edges.update(edges)
    subjects.update({pair[0] for pair in edges})
    objects.update({pair[1] for pair in edges})
    subjects_list = list(subjects)
    objects_list = list(objects)
    attempts = 0

    while len(out) < count and attempts < max_attempts and subjects and objects:
        subject = random.choice(subjects_list)
        object = random.choice(objects_list)
        pair = (subject, object)
        attempts += 1

        if pair in forbidden_edges or pair in out:
            continue

        triple = (pair[0], predicate, pair[1])
        fits_domain = ontology.fits_domain_range(triple, knowledge_graph, type_predicate, check_domain=True, check_range=False)
        fits_range = ontology.fits_domain_range(triple, knowledge_graph, type_predicate, check_domain=False, check_range=True)

        if fits_domain and fits_range:
            out.add(pair)
            attempts = 0
        else:
            if not fits_domain:
                subjects.discard(subject)
                subjects_list = list(subjects)
            if not fits_range:
                objects.discard(object)
                objects_list = list(objects)

    return out


def get_random_negative_examples(knowledge_graph, predicate, set_size, already_selected: set[tuple], max_attempts=None) -> set[tuple]:
    out = set()
    already_selected = already_selected or set()
    forbidden_pairs = set(knowledge_graph.get_edges(predicate))

    subset_size = max(set_size * 5, 100)

    raw_subs = knowledge_graph.get_all_subjects()
    raw_objs = knowledge_graph.get_all_objects()

    all_subs = tuple(raw_subs) if isinstance(raw_subs, set) else raw_subs
    all_objs = tuple(raw_objs) if isinstance(raw_objs, set) else raw_objs

    k_subs = min(len(all_subs), subset_size)
    k_objs = min(len(all_objs), subset_size)

    if k_subs == 0 or k_objs == 0:
        return out

    sub_pool = random.sample(all_subs, k_subs)
    obj_pool = random.sample(all_objs, k_objs)

    if max_attempts is None:
        max_attempts = set_size * 20
    attempts = 0

    while len(out) < set_size and attempts < max_attempts:
        attempts += 1
        s = random.choice(sub_pool)
        o = random.choice(obj_pool)
        pair = (s, o)

        if pair in forbidden_pairs or pair in already_selected or pair in out:
            continue

        out.add(pair)

    return out