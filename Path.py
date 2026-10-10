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

    def frontiers(self) -> Entity | None:
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

    def to_closed_rule(self, resolve_to_uri) -> Rule:
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
        name_dict = {self.head[0]: {0}}
        if self.head[0] != self.head[2]:
            name_dict[self.head[2]] = {1}
        else:
            name_dict[self.head[0]].add(1)
        nodes = self.get_nodes()
        node = self.head[0]
        reflexive_triples = []
        triple_set = set()
        count = 2
        while nodes:
            next_triple = None
            nodes.discard(node)

            for s, p, o in self.body:
                if node not in (s, o):
                    continue
                if s == o:
                    reflexive_triples.append((s, p, o))
                elif s == node and o in nodes:
                    next_triple = (s, p, o)
                    next_node = o
                elif o == node and s in nodes:
                    next_triple = (s, p, o)
                    next_node = s

            if reflexive_triples:
                reflexive_triples.sort()

                for s, p, o in reflexive_triples:
                    var_s = count
                    var_o = count + 1
                    count += 2

                    name_dict[s].add(var_s)
                    name_dict[o].add(var_o)
                    triple_set.add((var_s, p, var_o))

                reflexive_triples.clear()

            if next_triple:
                var_s = count
                var_o = count + 1
                count += 2

                s, p, o = next_triple
                if s in name_dict:
                    name_dict[s].add(var_s)
                else:
                    name_dict[s] = {var_s}

                if o in name_dict:
                    name_dict[o].add(var_o)
                else:
                    name_dict[o] = {var_o}

                triple_set.add((var_s, p, var_o))
            else:
                break

            node = next_node

        return Rule(body_vars, head_vars, triple_set, { tuple(c) for c in name_dict.values() if len(c) > 1 }, resolve_to_uri)

    def __repr__(self):
        return f"Path(head={self.head}, body={self.body})"
