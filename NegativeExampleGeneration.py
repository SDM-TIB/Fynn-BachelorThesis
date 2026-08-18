import re
from rdflib import URIRef, RDF, SH, Graph
from KnowledgeGraph.Graph import Graph as KG

class TriplePattern:
    def __init__(self, predicate: URIRef, object_value: URIRef, in_filter: bool = False, is_not_exists: bool = False):
        self.predicate = predicate
        self.object = object_value
        self.in_filter = in_filter
        self.is_not_exists = is_not_exists

    def __str__(self):
        return f"({self.predicate}, {self.object}, {'NOT ' if self.is_not_exists else ''}FILTER)" if self.in_filter else f"({self.predicate}, {self.object})"
    def __repr__(self):
        return self.__str__()

def generate_negative_triples(graph: KG, report_path, constraint_path) -> set[tuple[str, str, str]]:
    constraint_patterns = process_shacl_shapes(constraint_path)
    violations = process_validation_report(report_path)

    negative_triples: set[tuple[str, str, str]] = set()
    for subject_uri, shape_uri in violations:
        subject = URIRef(subject_uri)
        patterns = constraint_patterns.get(shape_uri)
        if not patterns:
            continue

        condition_patterns = [p for p in patterns if not p.in_filter]
        filter_patterns = [p for p in patterns if p.in_filter]
        matches_conditions = True
        for pattern in condition_patterns:
            if not check_pattern_match(graph, subject, pattern):
                matches_conditions = False
                break

        if matches_conditions:
            for s, p, o in graph.get_triples(graph.clean_uri(str(subject))):
                #TODO: Check what to do about blank nodes
                for pattern in filter_patterns:
                    predicate = graph.clean_uri(str(pattern.predicate))
                    object = graph.clean_uri(str(pattern.object)) if pattern.object else None
                    if p == predicate and (object is None or object == o):
                        negative_triples.add((s, p, o))

    return negative_triples

def extract_triple_patterns(query_text: str) -> list[TriplePattern]:
    """
    Extracts triple patterns from a given SPARQL query text.

    This function parses a SPARQL query text and identifies triple patterns. It separates
    patterns within the main query and those within FILTER EXISTS/NOT EXISTS blocks, if present.
    Triple patterns are then categorized and stored along with their context information such
    as whether they are part of a filter and if NOT EXISTS was used.

    Args:
        query_text (str): The SPARQL query text from which to extract triple patterns.

    Returns:
        List[TriplePattern]: A list of extracted triple patterns, each represented as an
        instance of TriplePattern.
    """

    patterns = []

    filter_not_exists_match = re.search(r'FILTER NOT ?EXISTS\s?\{([^}]+)\}', query_text)
    filter_exists_match = re.search(r'FILTER ?EXISTS\s?\{([^}]+)\}', query_text)

    main_query = query_text
    filter_exists_query = ""
    filter_not_exists_query = ""

    if filter_exists_match:
        filter_exists_query = filter_exists_match.group(1)
        if filter_not_exists_match:
            filter_not_exists_query = filter_not_exists_match.group(1)

            main_query = "".join([query_text[:min(filter_exists_match.start(), filter_not_exists_match.start())],
                                  query_text[min(filter_exists_match.end(), filter_not_exists_match.end()):max(
                                      filter_exists_match.start(), filter_not_exists_match.start())],
                                  query_text[max(filter_exists_match.end(), filter_not_exists_match.end()):]])
        else:
            main_query = query_text[:filter_exists_match.start()]
    elif filter_not_exists_match:
        filter_not_exists_query = filter_not_exists_match.group(1)
        main_query = query_text[:filter_not_exists_match.start()]

    def extract_from_text(text: str, in_filter: bool, is_not_exists) -> None:
        # Direct patterns with $this
        direct_matches = re.finditer(r'\$this\s+<([^>]+)>\s+(?:<([^>]+)>|\?(\w+))', text)
        for match in direct_matches:
            pred = URIRef(match.group(1).strip())
            obj = URIRef(match.group(2).strip()) if match.group(2) else None
            patterns.append(TriplePattern(pred, obj, in_filter, is_not_exists if in_filter else False))

        # Indirect patterns with variables
        var_matches = re.finditer(r'\?(\w+)\s+<([^>]+)>\s+\?(\w+)', text)
        for match in var_matches:
            pred = URIRef(match.group(2).strip())
            patterns.append(TriplePattern(pred, None, in_filter, is_not_exists if in_filter else False))

    extract_from_text(main_query, False, False)
    if filter_exists_query:
        extract_from_text(filter_exists_query, True, False)

    if filter_not_exists_query:
        extract_from_text(filter_not_exists_query, True, True)

    return patterns

def process_shacl_shapes(shacl_file: str) -> dict[str, list[TriplePattern]]:
    """
    Processes the provided SHACL (Shapes Constraint Language) file to extract and return
    a dictionary of SHACL NodeShapes and their associated SPARQL triple patterns. The
    function parses the SHACL file into a graph, identifies NodeShapes, and retrieves
    any SPARQL queries and their corresponding triple patterns.

    Args:
        shacl_file (str): Path to the SHACL Turtle file to be processed.

    Returns:
        dict[str, list[TriplePattern]]: A dictionary mapping SHACL NodeShapes to lists
        of extracted SPARQL triple patterns.
    """

    shapes_graph = Graph()
    shapes_graph.parse(shacl_file, format='turtle')

    constraint_patterns = {}

    for shape in shapes_graph.subjects(RDF.type, SH.NodeShape):
        for sparql in shapes_graph.objects(shape, SH.sparql):
            query = str(shapes_graph.value(sparql, SH.select))
            patterns = extract_triple_patterns(query)
            if patterns:
                constraint_patterns[str(shape)] = patterns

    return constraint_patterns

def process_validation_report(report_file: str) -> list[tuple[str, str]]:
    """
    Processes a SHACL validation report and extracts violations as tuples containing
    focus node and source shape.

    The function reads the validation report file, adds necessary RDF prefixes, parses
    the data into a graph, and extracts all validation results. From these results, it
    collects the focus node and source shape for each violation.

    Args:
        report_file (str): Path to the SHACL validation report file in Turtle format.

    Returns:
        List[Tuple[str, str]]: A list of tuples where each tuple contains the focus
        node and source shape for a validation violation.
    """

    with open(report_file, 'r', encoding='utf-8') as f:
        content = f.read()

    prefixes = """
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        @prefix : <http://example.org/> .
    """
    modified_content = prefixes + content

    report_graph = Graph()
    report_graph.parse(data=modified_content, format='turtle')

    violations = []
    validation_results = list(report_graph.subjects(RDF.type, SH.ValidationResult))

    for result in validation_results:
        focus_node = report_graph.value(result, SH.focusNode)
        source_shape = report_graph.value(result, SH.sourceShape)
        if focus_node and source_shape:
            violations.append((str(focus_node), str(source_shape)))

    return violations

def check_pattern_match(graph: KG, subject: URIRef, pattern: TriplePattern) -> bool:
    """
    Check if a given pattern matches a specific subject in the graph.

    This function evaluates whether a given triple pattern matches a subject within
    a graph. It considers the `is_not_exists` flag in the provided pattern to
    determine logical negation of the match result.

    Args:
        graph (Graph): The RDF graph to be searched for matching triples
        subject (URIRef): The RDF subject to be matched in the graph
        pattern (TriplePattern): The triple pattern against which the match is
            evaluated. Contains information on the predicate, object, and the
            `is_not_exists` flag

    Returns:
        bool: Returns True if the pattern matches the subject in the given graph, or
            if the pattern fails to match and `is_not_exists` is True. Otherwise,
            returns False.
    """
    subject = graph.clean_uri(str(subject))
    predicate = graph.clean_uri(str(pattern.predicate))
    object = graph.clean_uri(str(pattern.object)) if pattern.object else None
    has_match = bool(graph.get_triples(subject, predicate, object))
    return not has_match if pattern.is_not_exists else has_match
