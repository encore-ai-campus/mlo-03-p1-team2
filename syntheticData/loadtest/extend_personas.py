"""Append new synthetic personas to syntheticData/personas.json without touching existing ones.

Run from the repository root:
    python syntheticData/loadtest/extend_personas.py --target 200

- Existing users (id, name, email, MBTI, weights, style, bio) are kept byte-for-byte equal.
- New users get numbers count+1..target, unique ids/names/emails, and MBTI/persona
  assignments that keep the whole dataset balanced (validate_dataset passes).
- If the file already has `target` users it does nothing. Any other count is an error.
- The original 100-user file is preserved as syntheticData/personas.v100.json
  (the earlier Playwright runs and their verifiers use that snapshot).
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import generatePersonas as gp  # noqa: E402

PROFILES = ROOT / 'personas.json'
SNAPSHOT = ROOT / 'personas.v100.json'
EXTENSION_SEED = 'loadtest-extension-v1'


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fill_deficits(choices: tuple, existing: list, new_count: int, rng: random.Random) -> list:
    """Assignments for new users so the final distribution differs by at most 1."""
    total = len(existing) + new_count
    have = Counter(existing)
    base, extra = divmod(total, len(choices))
    order = list(choices)
    rng.shuffle(order)
    # Types that already have more get the +1 slots first so no target is below current.
    order.sort(key=lambda c: -have[c])
    targets = {c: base + (1 if i < extra else 0) for i, c in enumerate(order)}
    if any(have[c] > targets[c] for c in choices):
        raise ValueError('Existing distribution cannot be balanced by appending')
    out = [c for c in choices for _ in range(targets[c] - have[c])]
    rng.shuffle(out)
    assert len(out) == new_count
    return out


def extend(data: dict, target: int) -> dict:
    users = data['users']
    start = len(users)
    new_count = target - start
    seed = data['metadata']['seed']
    rng = random.Random(f'{seed}:{EXTENSION_SEED}:{start}->{target}')
    personas = fill_deficits(tuple(gp.PERSONA_WEIGHTS), [u['persona'] for u in users], new_count, rng)
    mbtis = fill_deficits(gp.MBTI_TYPES, [u['mbti'] for u in users], new_count, rng)
    used_names = {u['name'] for u in users}
    names = rng.sample([n for n in gp.NAME_POOL if n not in used_names], new_count)
    style_rng = random.Random(f'{seed}:{EXTENSION_SEED}:viewing-style')
    new_users = []
    for offset, (persona, mbti, name) in enumerate(zip(personas, mbtis, names)):
        number = start + offset + 1
        weights = gp.category_weights(persona, rng)
        preferred = sorted(gp.CATEGORIES, key=lambda c: -weights[c])[:2]
        companion, frequency, discovery = style_rng.choice(gp.STYLE_OPTIONS)
        style = {'companion': companion, 'attendance_frequency': frequency, 'discovery_style': discovery}
        new_users.append({
            'id': str(uuid.uuid5(gp.ID_NAMESPACE, f'{seed}:{number}')),
            'name': name,
            'email': f'persona{number:04d}@example.com',
            'mbti': mbti,
            'persona': persona,
            'preferred_categories': preferred,
            'category_weights': weights,
            'viewing_style': style,
            'bio': gp.profile_bio(preferred, style),
        })
    metadata = dict(data['metadata'])
    metadata['count'] = target
    metadata.setdefault('extensions', []).append({
        'from_count': start, 'to_count': target, 'seed': EXTENSION_SEED,
        'generator': 'syntheticData/loadtest/extend_personas.py',
        'base_snapshot': SNAPSHOT.name,
    })
    out = {'metadata': metadata, 'users': users + new_users}
    gp.validate_dataset(out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--target', type=int, default=200)
    args = parser.parse_args()
    data = json.loads(PROFILES.read_text(encoding='utf-8'))
    count = len(data['users'])
    if count == args.target:
        print(f'personas.json already has {count} users; nothing to do')
        return 0
    if count != 100 or data['metadata']['count'] != 100:
        print(f'Unexpected user count {count}; refusing to modify', file=sys.stderr)
        return 1
    if SNAPSHOT.exists() and SNAPSHOT.read_bytes() != PROFILES.read_bytes():
        print('personas.v100.json exists and differs from personas.json; refusing', file=sys.stderr)
        return 1
    SNAPSHOT.write_bytes(PROFILES.read_bytes())
    extended = extend(data, args.target)
    assert extended['users'][:count] == data['users']
    PROFILES.write_text(json.dumps(extended, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'added {args.target - count} users; base sha256 {sha256(SNAPSHOT)}; new sha256 {sha256(PROFILES)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
