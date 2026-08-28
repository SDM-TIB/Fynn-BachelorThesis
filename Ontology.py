from rdflib import Graph, RDF, RDFS, OWL
from KnowledgeGraph.Graph import Graph as KG
from rdflib.plugins.parsers.notation3 import BadSyntax

class Ontology:
    def __init__(self, classes=None, properties=None):
        self.classes = classes if classes is not None else dict()
        self.properties = properties if properties is not None else dict()

    def get_name(self, node):
        return str(node).strip("<>").split('/')[-1].split('#')[-1]

    def add_class(self, c: str, super_class: str = ""):
        classname = c
        if classname not in self.classes:
            self.classes[classname] = set()
        if super_class:
            super_name = super_class
            self.classes[classname].add(super_name)

    def add_property(self, p: str, d=None, r=None):
        p_name = p
        domains = {x for x in d} if d else set()
        ranges = {x for x in r} if r else set()

        if p_name not in self.properties:
            self.properties[p_name] = (domains, ranges)
        else:
            self.properties[p_name][0].update(domains)
            self.properties[p_name][1].update(ranges)

    def get_all_supertypes(self, class_name: str) -> set[str]:
        """Recursively collects all direct and indirect superclasses (transitive closure)."""
        visited = set()
        queue = [class_name]

        while queue:
            curr = queue.pop(0)
            if curr not in visited:
                visited.add(curr)
                parents = self.classes.get(curr, set())
                queue.extend(parents - visited)

        return visited

    def fits_domain_range(self, triple, kg: KG, type_predicate, check_domain=True, check_range=True):
        #TODO: Add support for literals and literal comparisons
        """
        Validates if a given triple (s, p, o) satisfies the ontology domain and range constraints.
        If domain/range are unspecified in the ontology for predicate p, it passes by default.
        """
        subject = kg.resolve_to_uri(triple[0])
        predicate = kg.resolve_to_uri(triple[1])
        obj = kg.resolve_to_uri(triple[2])
        p_name = self.get_name(predicate)
        if p_name not in self.properties:
            return True

        domain_types, range_types = self.properties[p_name]

        if check_domain and domain_types:
            s_types = self._get_entity_types(subject, kg, type_predicate)
            if not s_types:
                return False

            s_expanded_types = set()
            for t in s_types:
                s_expanded_types.update(self.get_all_supertypes(t))

            if not domain_types.intersection(s_expanded_types):
                return False

        if check_range and range_types:
            o_types = self._get_entity_types(obj, kg, type_predicate)
            if not o_types:
                return False

            o_expanded_types = set()
            for t in o_types:
                o_expanded_types.update(self.get_all_supertypes(t))

            if not range_types.intersection(o_expanded_types):
                return False

        return True

    def _get_entity_types(self, entity: str, kg: KG, type_predicate: str) -> set[str]:
        """Queries knowledge graph for all type classes associated with an entity."""
        types = set()
        entity = kg.clean_uri(entity)
        type_triples = kg.get_type(entity, type_predicate)
        for t in type_triples:
            types.add(self.get_name(t))
        return types


def parse_ontology(ontology_file: str) -> Ontology:
    """Parses a Turtle (.ttl) ontology file using RDFLib into an Ontology object."""
    g = Graph()
    try:
        g.parse(ontology_file, format='turtle')
    except BadSyntax as e:
        print(f"Syntax error in {ontology_file}:")
        print(f"Line {e.lines}: {e.msg}")
        raise e
    ontology = Ontology()

    def get_name(node):
        return str(node).split('/')[-1].split('#')[-1]

    for c in g.subjects(RDF.type, OWL.Class):
        ontology.add_class(get_name(c))
    for c in g.subjects(RDF.type, RDFS.Class):
        ontology.add_class(get_name(c))

    for sub, sup in g.subject_objects(RDFS.subClassOf):
        ontology.add_class(get_name(sub), get_name(sup))

    for p_type in [OWL.ObjectProperty, OWL.DatatypeProperty, RDF.Property]:
        for p in g.subjects(RDF.type, p_type):
            domains = {get_name(d) for d in g.objects(p, RDFS.domain)}
            ranges = {get_name(r) for r in g.objects(p, RDFS.range)}
            ontology.add_property(get_name(p), domains, ranges)

    return ontology