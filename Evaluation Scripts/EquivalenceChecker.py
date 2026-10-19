import argparse
import ast
import re
from collections import defaultdict
from itertools import permutations
from pathlib import Path


# Variables supported by the rule formats in the input files.
VARIABLE_PATTERN = re.compile(r"^(?:\?[A-Za-z_]\w*|v\d+)$")

# Matches both <http://example.org/predicate> and
# http://example.org/predicate, followed by a list of arguments.
ATOM_PATTERN = re.compile(
    r"(<[^>]+>|[^\s(),]+)\s*\(([^()]*)\)"
)


def is_variable(term: str) -> bool:
    """Return whether a term represents a variable."""
    return bool(VARIABLE_PATTERN.fullmatch(term))


def normalize_atom(predicate: str, arguments: list[str]) -> tuple:
    """Normalize an atom without changing its semantics."""
    predicate = predicate.strip()

    if predicate.startswith("<") and predicate.endswith(">"):
        predicate = predicate[1:-1]

    # Make abbreviated predicates and full IRIs comparable.
    # Example: http://yago-knowledge.org/resource/isMarriedTo
    #       -> isMarriedTo
    predicate = predicate.rstrip("/#").rsplit("/", 1)[-1].rsplit("#", 1)[-1]

    return predicate, tuple(arg.strip() for arg in arguments)


def parse_dictionary_rule(line: str) -> tuple | None:
    """Parse {'Head': '...', 'Body': '...'} rule syntax."""
    try:
        rule = ast.literal_eval(line)
    except (ValueError, SyntaxError):
        return None

    if not isinstance(rule, dict):
        return None

    if not isinstance(rule.get("Head"), str):
        return None

    if not isinstance(rule.get("Body"), str):
        return None

    def parse_triple(triple: str) -> tuple:
        terms = triple.split()

        if len(terms) != 3:
            raise ValueError(f"Invalid triple: {triple!r}")

        subject, predicate, obj = terms
        return normalize_atom(predicate, [subject, obj])

    head = parse_triple(rule["Head"])

    # The body contains triples separated by whitespace.
    # Each triple consists of exactly three tokens.
    body_terms = rule["Body"].split()

    if len(body_terms) % 3 != 0:
        raise ValueError(f"Invalid rule body: {rule['Body']!r}")

    body = [
        normalize_atom(body_terms[i + 1],
                       [body_terms[i], body_terms[i + 2]])
        for i in range(0, len(body_terms), 3)
    ]

    return head, tuple(body)


def parse_datalog_rule(line: str) -> tuple:
    """Parse a Datalog rule using ':-' and predicate(arg, arg) atoms."""
    if ":-" not in line:
        raise ValueError("Missing Datalog rule separator ':-'")

    head_text, body_text = line.split(":-", 1)

    def parse_atoms(text: str) -> list[tuple]:
        matches = list(ATOM_PATTERN.finditer(text))

        # Ensure that the entire input consists of valid atoms and
        # separators (commas and whitespace).
        remainder = ATOM_PATTERN.sub("", text)
        if remainder.strip(" \t\r\n,"):
            raise ValueError(f"Could not parse rule atoms: {remainder!r}")

        atoms = []

        for match in matches:
            predicate = match.group(1)
            arguments_text = match.group(2)
            arguments = [
                arg.strip()
                for arg in arguments_text.split(",")
            ]

            if not arguments_text.strip():
                arguments = []

            atoms.append(normalize_atom(predicate, arguments))

        return atoms

    head_atoms = parse_atoms(head_text)
    body_atoms = parse_atoms(body_text)

    if len(head_atoms) != 1:
        raise ValueError("Expected exactly one head atom")

    if not body_atoms:
        raise ValueError("Expected at least one body atom")

    return head_atoms[0], tuple(body_atoms)


def parse_rule(line: str) -> tuple:
    """Parse a rule in either supported format."""
    dictionary_rule = parse_dictionary_rule(line)

    if dictionary_rule is not None:
        return dictionary_rule

    return parse_datalog_rule(line)


def canonicalize_rule(rule: tuple) -> tuple:
    """
    Return a canonical representation invariant under variable renaming
    and body-atom reordering.

    Enumerating all variable assignments guarantees that equivalent
    rules receive the same representation.
    """
    head, body = rule

    variables = sorted({
        term
        for predicate, arguments in (head, *body)
        for term in arguments
        if is_variable(term)
    })

    def encode_atom(atom: tuple, mapping: dict) -> tuple:
        predicate, arguments = atom

        encoded_arguments = tuple(
            ("VAR", mapping[term]) if is_variable(term)
            else ("CONST", term)
            for term in arguments
        )

        return predicate, encoded_arguments

    best = None

    for ordering in permutations(variables):
        mapping = {
            variable: index
            for index, variable in enumerate(ordering)
        }

        encoded_head = encode_atom(head, mapping)
        encoded_body = tuple(sorted(
            encode_atom(atom, mapping) for atom in body
        ))

        signature = encoded_head, encoded_body

        if best is None or signature < best:
            best = signature

    # A rule with no variables has only one possible representation.
    if best is None:
        best = (
            encode_atom(head, {}),
            tuple(sorted(encode_atom(atom, {}) for atom in body)),
        )

    return best


def read_rules(directory: Path) -> dict[str, list[tuple]]:
    """Read and parse all .txt files in a directory."""
    rules_by_file = {}

    files = sorted(
        path for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() == ".txt"
    )

    if not files:
        raise FileNotFoundError(
            f"No .txt files found in {directory.resolve()}"
        )

    for path in files:
        rules = []

        with path.open("r", encoding="utf-8-sig") as file:
            for line_number, line in enumerate(file, start=1):
                line = line.strip()

                if not line:
                    continue

                try:
                    rule = parse_rule(line)
                    rules.append((line, rule))
                except ValueError as error:
                    raise ValueError(
                        f"{path.name}:{line_number}: {error}\n"
                        f"Input: {line}"
                    ) from error

        rules_by_file[path.name] = rules

    return rules_by_file


def generate_report(directory: Path) -> None:
    rules_by_file = read_rules(directory)

    # Each canonical signature identifies one distinct rule.
    groups = defaultdict(list)

    for filename, rules in rules_by_file.items():
        for original, parsed in rules:
            signature = canonicalize_rule(parsed)
            groups[signature].append((filename, original))

    total_rules = sum(len(rules) for rules in rules_by_file.values())
    distinct_rules = len(groups)

    # Number of additional occurrences of already-seen rules.
    equivalent_rules = total_rules - distinct_rules

    print("=" * 80)
    print("RULE COMPARISON REPORT")
    print("=" * 80)
    print(f"Directory:                  {directory.resolve()}")
    print(f"Files compared:             {len(rules_by_file)}")
    print(f"Total rule occurrences:     {total_rules}")
    print(f"Equivalent rule occurrences: {equivalent_rules}")
    print(f"Different rules:            {distinct_rules}")
    print()

    print("-" * 80)
    print("RULE COUNTS PER FILE")
    print("-" * 80)

    for filename, rules in rules_by_file.items():
        unique_in_file = {
            canonicalize_rule(parsed)
            for _, parsed in rules
        }

        print(
            f"{filename}: {len(rules)} rules, "
            f"{len(unique_in_file)} distinct rules"
        )

    print()
    print("-" * 80)
    print("DISTINCT RULES")
    print("-" * 80)

    for index, (signature, occurrences) in enumerate(
        sorted(groups.items(), key=lambda item: repr(item[0])),
        start=1,
    ):
        if len(occurrences) == len(rules_by_file):
            continue
        print(f"\nRule {index} (occurrences: {len(occurrences)})")

        # Display a representative original rule.
        filename, original = occurrences[0]
        print(f"  Representative ({filename}):")
        print(f"    {original}")

        if len(occurrences) > 1:
            print("  Equivalent occurrences:")
            for filename, original in occurrences:
                print(f"    [{filename}] {original}")

    print()
    print("=" * 80)
    print(
        f"SUMMARY: {distinct_rules} distinct rules, "
        f"{equivalent_rules} additional equivalent occurrences, "
        f"{total_rules} total occurrences."
    )
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Compare rules across .txt files, treating variable-renamed "
            "rules and reordered body atoms as equivalent."
        )
    )
    parser.add_argument(
        "--dir",
        required=True,
        type=Path,
        help="Directory containing the .txt files to compare.",
    )

    arguments = parser.parse_args()
    generate_report(arguments.dir)