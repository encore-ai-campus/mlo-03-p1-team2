"""Offline scheduling, checkpoint and evidence checks."""
import asyncio
from collections import Counter
from datetime import datetime, timezone
import json
import time


def safe_message(error, password):
    return str(error).replace(password, '[redacted]')


def check_server_identity(expected, actual):
    if (actual.get('collection') != 'simulation' or actual.get('run_id') != expected['run_id']
            or actual.get('instance_id') != expected['instance_id']):
        raise ValueError('Refusing a server that is not this simulation instance')


def retained_favorites(previous, current):
    return sorted(set(previous) | set(current))


def save_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    for attempt in range(8):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(0.025 * (attempt + 1))


async def run_bounded(items, worker, concurrency):
    semaphore = asyncio.Semaphore(concurrency)
    stopped = asyncio.Event()
    async def guarded(item):
        async with semaphore:
            if stopped.is_set():
                return
            try:
                return await worker(item)
            except Exception:
                stopped.set()
                raise
    return await asyncio.gather(*(guarded(item) for item in items), return_exceptions=True)


def compare_payload(expected, actual):
    fields = ('event_id', 'type', 'session_id', 'anonymous_id', 'page', 'props', 'schema_version')
    errors = [field for field in fields if expected.get(field) != actual.get(field)]
    def timestamp(value):
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        # BSON dates have millisecond precision.
        return int(value.astimezone(timezone.utc).timestamp() * 1000)
    if timestamp(expected['occurred_at']) != timestamp(actual['occurred_at']):
        errors.append('occurred_at')
    return errors


def visit_errors(visit, events):
    errors = []
    outcome = visit['plan']['outcome']
    types = {event['type'] for event in events}
    required = {'login', 'logout', 'category_select', 'performance_view'}
    if outcome in ('booking_abandon', 'payment_abandon', 'purchase'):
        required.add('booking_start')
    if outcome in ('payment_abandon', 'purchase'):
        required.add('reservation_request')
    if outcome == 'purchase':
        required.add('payment_complete')
    if required - types:
        errors.append('missing types: ' + ', '.join(sorted(required - types)))
    views = [e['props'] for e in events if e['type'] == 'performance_view']
    if Counter((e.get('performance_id'), e.get('category')) for e in views) != Counter(
            (e['performance_id'], e['category']) for e in visit['views']):
        errors.append('views differ from UI observations')
    if len(visit['views']) != visit['plan']['views']:
        errors.append('views differ from planned count')
    if any(e['category'] != visit['plan']['category'] for e in visit['views']):
        errors.append('view category differs from plan')
    session_ids = {e['session_id'] for e in events}
    if len(session_ids) != 1 or (visit.get('session_id') and session_ids != {visit['session_id']}):
        errors.append('session identity mismatch')
    for reservation in visit['reservations']:
        needed = ['reservation_request'] + (['payment_complete'] if outcome == 'purchase' else [])
        for kind in needed:
            matching = [e for e in events if e['type'] == kind and e['props'].get('reservation_id') == reservation['id']]
            if len(matching) != 1 or any(
                    e['props'].get('performance_id') != reservation['performance_id']
                    or e['props'].get('quantity') != reservation['quantity'] for e in matching):
                errors.append(f'{kind} reservation reference mismatch')
    if outcome in ('view_only', 'favorite_only', 'booking_abandon') and (
            visit['reservations'] or types & {'reservation_request', 'payment_complete'}):
        errors.append('unexpected reservation conversion')
    return errors
