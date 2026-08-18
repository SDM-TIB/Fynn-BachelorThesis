from typing import Optional

from rdflib import URIRef, Literal, Node


# def clean_uri(uri: str | int | None | URIRef | Literal | Node, prefix: Optional[str] = None) -> str | int | None:
#     """Removes RDF formatting syntax (<>, spaces) and optionally strips prefixes."""
#     if uri is None:
#         return None
#     if isinstance(uri, int):
#         return uri
#     token = uri.strip("<> \n\r\t")
#     if prefix and token.startswith(prefix):
#         return token[len(prefix) :]
#     return token

# def restore_uri(uri, prefix: str) -> str:
#     return f"<{prefix}{uri}>"