"""Preserve historical persona inputs before extending the shared dataset."""
import hashlib
import json
from pathlib import Path

from syntheticData.generatePersonas import expand_personas, validate_dataset
from syntheticData.playwright.load_control import save
from syntheticData.playwright.scenarios import profiles_for_run


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expand_file(path, artifacts, target=300):
    path, artifacts = Path(path), Path(artifacts)
    data = json.loads(path.read_text(encoding='utf-8'))
    validate_dataset(data)
    if len(data['users']) == target:
        return data
    if len(data['users']) != 100:
        raise ValueError('Expected 100 original profiles or 300 already prepared profiles')
    expanded = expand_personas(data, target)
    histories = list(artifacts.glob('*/state.json'))
    # Validate every existing campaign first, before changing any shared input.
    sources = [(p.parent, profiles_for_run(p.parent, path)) for p in histories]
    for directory, source in sources:
        snapshot = directory / 'profiles-input.json'
        if not snapshot.exists():
            snapshot.write_bytes(source.read_bytes())
    save(path, expanded)
    return expanded
