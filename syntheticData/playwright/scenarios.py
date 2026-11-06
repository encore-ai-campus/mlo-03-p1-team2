"""Deterministic fictional behavior; no network calls or profile writes."""

import copy
import hashlib
import random


OUTCOMES = ('view_only', 'favorite_only', 'booking_abandon', 'payment_abandon', 'purchase')
SESSION_COUNTS = {'occasional': 1, 'monthly': 2, 'frequent': 3}
OUTCOME_WEIGHTS = {
    'occasional': (45, 25, 15, 5, 10),
    'monthly': (30, 25, 20, 5, 20),
    'frequent': (20, 25, 20, 5, 30),
}
REVISIT_PROBABILITY = {'familiar': 0.8, 'mixed': 0.4, 'adventurous': 0.0}


def synthetic_email(email):
    local, separator, domain = email.lower().partition('@')
    if not separator or domain != 'example.com' or '+' in local:
        raise ValueError('Only untagged example.com persona addresses are allowed')
    return f'{local}+synthetic@{domain}'


def build_plan(users, seed=42):
    plans = []
    for index, user in enumerate(users):
        # Per-person stream makes expanding 3 -> 100 preserve the first 3 plans.
        rng = random.Random(f'{seed}:{user["id"]}')
        style = user['viewing_style']
        frequency = style['attendance_frequency']
        sessions = []
        for number in range(SESSION_COUNTS[frequency]):
            outcome = (('view_only', 'booking_abandon', 'purchase')[index] if index < 3
                       else rng.choices(OUTCOMES, OUTCOME_WEIGHTS[frequency])[0])
            companion = style['companion']
            quantities = {'solo': (1,), 'partner': (2,), 'friends': (2, 3, 4), 'family': (2, 3, 4)}
            weights = user['category_weights']
            sessions.append({
                'index': number,
                'outcome': outcome,
                'category': rng.choices(list(weights), list(weights.values()))[0],
                'views': rng.randint(1, 3),
                'quantity': rng.choice(quantities[companion]),
                'revisit_probability': REVISIT_PROBABILITY[style['discovery_style']],
                'selection_seed': rng.randrange(2**32),
            })
        plans.append({'persona_id': user['id'], 'name': user['name'], 'mbti': user['mbti'],
                      'source_email': user['email'], 'email': synthetic_email(user['email']),
                      'sessions': sessions})
    return plans


def tag_events(events, tags):
    result = copy.deepcopy(events)
    for event in result:
        event.setdefault('props', {}).update({
            'synthetic': True,
            'synthetic_run_id': tags['run_id'],
            'synthetic_persona_id': tags['persona_id'],
            'synthetic_scenario': tags['scenario'],
        })
        if len(event['props']) > 20:
            raise ValueError('Synthetic tags exceed the tracking props limit')
    return result


def check_resume(state, fingerprint):
    if state['fingerprint'] != fingerprint:
        raise ValueError('Profiles, target or seed changed; use a new run ID')


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def session_pending(record):
    if record is None:
        return True
    if record.get('status') == 'complete':
        return False
    raise ValueError('An incomplete session may have side effects; inspect state and DB before retrying')
