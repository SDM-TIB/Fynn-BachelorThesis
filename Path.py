from Rule import Rule
Entity = str | int

class Path:
    """
    Represents a specific instantiation of a rule in the Knowledge Graph.
    """
    def __init__(self, head: tuple[Entity, Entity, Entity], body: set[tuple[Entity, Entity, Entity]]):
        self.head = head
        self.body = body

    def copy(self):
        return Path(self.head, self.body.copy())

    def get_nodes(self) -> set[Entity]:
        nodes = set()
        for s, p, o in self.body:
            nodes.add(s)
            nodes.add(o)
        return nodes

    def frontiers_closed_rule(self) -> Entity:
        h1 = self.head[0]
        nodes = self.get_nodes()
        if not self.body or (len(nodes) == 1 and h1 in nodes):
            return h1

        counts: dict[Entity, int] = {}
        for s, p, o in self.body:
            if s == o:
                continue
            counts[s] = counts.get(s, 0) + 1
            counts[o] = counts.get(o, 0) + 1

        for node, count in counts.items():
            if node == h1:
                continue
            if count == 1:
                return node
        
        return None

    def to_rule_closed_rule(self) -> Rule:
        entity_to_var: dict[Entity, int] = {self.head[0]: 0, self.head[2]: 1}
        next_var = 2

        def get_var(entity: Entity) -> int:
            nonlocal next_var
            if entity not in entity_to_var:
                entity_to_var[entity] = next_var
                next_var += 1
            return entity_to_var[entity]

        body_vars: set[tuple[int, Entity, int]] = set()
        for s, p, o in self.body:
            body_vars.add((get_var(s), p, get_var(o)))
        
        head_vars = (entity_to_var[self.head[0]], self.head[1], entity_to_var[self.head[2]])
        return Rule(body_vars, head_vars)

    def __repr__(self):
        return f"Path(head={self.head}, body={self.body})"
