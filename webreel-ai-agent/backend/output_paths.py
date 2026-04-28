"""
Helpers for resolving the shared output directory and public video URLs.
"""

from __future__ import annotations

import os
from pathlib import Path


def resolve_output_dir() -> Path:
    """Return the output root used by API and workers."""
    configured = os.getenv("OUTPUT_DIR")
    if configured:
        return Path(configured)

    docker_output = Path("/app/output")
    if docker_output.exists():
        return docker_output

    return Path(__file__).resolve().parent.parent / "output"


def build_video_url(video_path: str | Path) -> str:
    """Build a /videos URL from a file inside the output directory."""
    path = Path(video_path)
    output_dir = resolve_output_dir()

    try:
        relative_path = path.resolve().relative_to(output_dir.resolve())
        return f"/videos/{relative_path.as_posix()}"
    except Exception:
        return f"/videos/{path.name}"
