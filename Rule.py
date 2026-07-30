from typing import Any

VariableID = int

class Rule:
    def __init__(self, body: set[tuple[VariableID, str | int, VariableID]], head: tuple[VariableID, str |int, VariableID]):
        self.body = body
        self.head = head

    def __repr__(self) -> str:
        body_str = ", ".join([f"{p}(v{s}, v{o})" for s, p, o in self.body])
        return f"{self.head[1]}(v{self.head[0]}, v{self.head[2]}) :- {body_str}"

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