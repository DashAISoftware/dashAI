import hashlib


def hash_function(content) -> str:
    """
    Generate a SHA-256 hash for the given content bytes.

    Args:
        content (bytes): The content to hash.
    """
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()
