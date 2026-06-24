import re
from pathlib import Path


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename to prevent path traversal and injection.

    Args:
        filename: Original filename from user upload
        max_length: Maximum allowed filename length

    Returns:
        Safe filename containing only alphanumeric, dash, underscore

    Rules:
    - Remove path separators (/, \\, ..)
    - Remove null bytes
    - Keep only alphanumeric, dash, underscore, dot
    - Replace whitespace with underscore
    - Limit length to max_length
    - Return lowercase
    """
    safe_name = Path(filename).name

    safe_name = safe_name.replace('\x00', '')

    safe_name = re.sub(r'\s+', '_', safe_name)

    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '', safe_name)

    safe_name = safe_name.strip('.-')

    if len(safe_name) > max_length:
        name, ext = Path(safe_name).stem, Path(safe_name).suffix
        max_name_len = max_length - len(ext)
        safe_name = name[:max_name_len] + ext

    if not safe_name:
        safe_name = "unnamed"

    return safe_name.lower()