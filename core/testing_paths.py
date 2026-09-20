"""Portable path fixture helper for regression tests; no source-data acquisition."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def portable_path(path, recorded_dataset_ref, root=ROOT):
    """Rebase a historical repository path; never access the original host path."""
    old_root = Path(recorded_dataset_ref).parents[3]
    relative = Path(path).relative_to(old_root) if Path(path).is_absolute() else Path(path)
    result = (root / relative).resolve()
    result.relative_to(root.resolve())
    return result
