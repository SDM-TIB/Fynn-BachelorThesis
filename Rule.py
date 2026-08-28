import time

VariableID = int

class Rule:
    def __init__(self, body: set[tuple[VariableID, str | int, VariableID]], head: tuple[VariableID, str |int, VariableID], resolve_to_uri):
        self.body = body
        self.head = head
        self.resolve_to_uri = resolve_to_uri
        self.time = time.time()

    def __repr__(self) -> str:
        body_str = ", ".join([f"{self.resolve_to_uri(p)}(v{s}, v{o})" for s, p, o in self.body])
        return f"{self.resolve_to_uri(self.head[1])}(v{self.head[0]}, v{self.head[2]}) :- {body_str}"

    def __hash__(self) -> int:
        return hash((frozenset(self.body), self.head))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rule):
            return False
        return self.body == other.body and self.head == other.head

    def is_valid(self) -> bool:
        head_s = self.head[0]
        head_o = self.head[2]
        counts = {}

        counts[head_s] = counts.get(head_s, 0) + 1
        counts[head_o] = counts.get(head_o, 0) + 1

        for s, p, o in self.body:
            counts[s] = counts.get(s, 0) + 1
            counts[o] = counts.get(o, 0) + 1

        if counts.get(head_o, 0) >= 2:
            if head_s == head_o:
                return counts[head_s] >= 4
            return True
        return False

    def get_as_string(self, resolve_to_uri, seperator: str) -> str:
        head_s = self.head[0]
        head_p = resolve_to_uri(self.head[1])
        head_o = self.head[2]
        body_string = ""
        for s, p, o in self.body:
            triple_string = f"  v{s}  {resolve_to_uri(p)}  v{o}"
            body_string += triple_string
        return f"v{head_s}{seperator}{head_p}{seperator}v{head_o}{seperator}{body_string}"

def get_as_tsv(rules: list[Rule], resolve_to_uri):
    lines = ["Head Subject\tHead Predicate\tHead Object\tBody"]
    for rule in rules:
        lines.append(rule.get_as_string(resolve_to_uri, seperator="\t"))
    return "\n".join(lines)

def get_as_csv(rules: list[Rule], resolve_to_uri):
    lines = ["Head Subject,Head Predicate,Head Object,Body"]
    for rule in rules:
        lines.append(rule.get_as_string(resolve_to_uri, seperator=","))
    return "\n".join(lines)

def get_for_analysis(rules: list[Rule], kg_name, approach, multiprocess: bool, start_time):
    lines = ["test,approach,answer,time"]
    i = 1
    rules.sort(key=lambda rule: rule.time)
    for rule in rules:
        lines.append(f"{kg_name},{approach}{"_MP" if multiprocess else ""},{i},{rule.time-start_time}")
        i += 1
    return "\n".join(lines)