from typing import Optional

def clean_uri(uri: str | int, prefix: Optional[str] = None) -> str | int | None:
    """Removes RDF formatting syntax (<>, spaces) and optionally strips prefixes."""
    if uri is None:
        return None
    if isinstance(uri, int):
        return uri
    token = uri.strip("<> \n\r\t")
    if prefix and token.startswith(prefix):
        return token[len(prefix) :]
    return token

def restore_uri(uri, prefix: str) -> str:
    return f"<{prefix}{uri}>"