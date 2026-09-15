"""Strict opt-in revalidation of local, non-redistributed source data.

Run: .venv/bin/python tools/validate_local_real_sources.py
Missing files are errors, never a successful real-data acceptance or a skip.
Public CI validates recorded evidence and runs the redistributable furnace fixture.
"""
import gzip
import hashlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def read(name):
    return json.loads((ROOT / name).read_text())


def portable_path(path, recorded_dataset_ref, root=ROOT):
    """Rebase a historical repository path; never access the original host path."""
    old_root = Path(recorded_dataset_ref).parents[3]
    relative = Path(path).relative_to(old_root) if Path(path).is_absolute() else Path(path)
    result = (root / relative).resolve()
    result.relative_to(root.resolve())
    return result


def validate():
    import numpy as np
    import pandas as pd
    from integrations.standardization.standard_agent.engine import StandardizationAgent
    record = read('three_scene_real_runtime.json')
    bf = next(s['receipt'] for s in record['scenes'] if s['scene'] == 'blast_furnace')
    candidates = record['candidates'] + read('datasets/real_validation/closeout/candidates.json')
    checked = set()
    for c in candidates:
        if c.get('local_path') and c.get('sha256'):
            path = portable_path(c['local_path'], bf['dataset_ref'])
            if hashlib.sha256(path.read_bytes()).hexdigest() != c['sha256']:
                raise ValueError(f'Source hash mismatch: {path}')
            checked.add(path)
    tobacco = ROOT/'runtime/data_validation/final_search/tobacco.xlsx'
    assert hashlib.sha256(tobacco.read_bytes()).hexdigest() == read('datasets/real_validation/tobacco_acquisition_manifest.json')['output_hash']
    frame = pd.read_csv(ROOT/'runtime/data_validation/real_search/stevenshaw_debutanizer.csv')
    assert frame.shape == (2394, 8)
    mapping = StandardizationAgent().map_columns(list(frame), 'debutanizer_column', frame)
    assert {'timestamp', 'bottom_temperature_b'}.issubset(mapping['missing_required'])
    assert mapping['required_coverage'] < 1
    values = np.loadtxt(io.BytesIO(gzip.decompress((ROOT/'runtime/data_validation/public_candidates/daisy_dryer.gz').read_bytes())))
    assert values.shape == (867, 7) and not np.isnan(values).any() and (values[:, -1] < 0).any()
    description = (ROOT/'runtime/data_validation/public_candidates/daisy_dryer_description.txt').read_text()
    assert 'fuel flow rate' in description and 'moisture content of raw material' in description
    print(f'Local source revalidation PASS: {len(checked)} source hashes; tobacco extraction; debutanizer and DAISY rejection checks. Both scenes remain UNAVAILABLE.')


if __name__ == '__main__':
    validate()
