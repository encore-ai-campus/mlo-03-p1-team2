"""Run real persona interactions through the existing Tikit UI.

No source files or DB tables are changed by this script. Service API calls
from the browser create test data. See playwrightGuide.md before running.
"""

import argparse
import asyncio
from collections import Counter
from datetime import date, datetime, timezone
import json
from pathlib import Path
import random
import re
import secrets
import sys
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen
import uuid

from scenarios import build_plan, check_resume, file_sha256, session_pending, tag_events, profiles_for_run
from safety import save_json, safe_message, run_bounded, visit_errors, check_server_identity
from transport import OBSERVE_TRACKING, DRAIN_TRACKING


HERE = Path(__file__).resolve().parent
PROFILES = HERE.parent / 'personas.json'


def append_json(path, value):
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + '\n')


class Campaign:
    def __init__(self, args):
        self.args = args
        self.directory = HERE / 'artifacts' / args.run_id
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'state.json'
        self.profile_path = profiles_for_run(self.directory, PROFILES)
        fingerprint = {'base_url': args.base_url.rstrip('/'), 'profiles_sha256': file_sha256(self.profile_path),
                       'seed': args.seed, 'collection': 'events', 'generator_version': '1.0'}
        if self.path.exists():
            self.state = json.loads(self.path.read_text(encoding='utf-8'))
            check_resume(self.state, fingerprint)
        else:
            self.state = {'run_id': args.run_id, 'synthetic': True, 'fingerprint': fingerprint,
                          'started_at': datetime.now(timezone.utc).isoformat(),
                          'password': secrets.token_urlsafe(24), 'accounts': {}}
            self.save()
        self.plans = build_plan(json.loads(self.profile_path.read_text(encoding='utf-8'))['users'], args.seed)

    def check_server(self):
        self.server = json.loads((self.directory / 'server.json').read_text(encoding='utf-8'))
        if self.server['base_url'] != self.args.base_url:
            raise ValueError('Browser URL differs from guarded server URL')
        request = Request(self.args.base_url + '/api/v1/simulation-check',
                          headers={'X-Tikit-Simulation-Key': self.server['key']})
        with urlopen(request, timeout=5) as response:
            check_server_identity(self.server, json.load(response))

    def save(self):
        save_json(self.path, self.state)

    def check_pilot(self):
        if self.args.count <= 3:
            return
        path = self.directory / 'verification-3.json'
        if not path.exists():
            raise ValueError('Run and verify the 3-person pilot before expanding')
        report = json.loads(path.read_text(encoding='utf-8'))
        if not report.get('passed') or report.get('fingerprint') != self.state['fingerprint']:
            raise ValueError('Pilot verification does not match this campaign')


class UserBrowser:
    def __init__(self, campaign, plan):
        self.campaign, self.plan = campaign, plan
        self.account = campaign.state['accounts'].setdefault(plan['persona_id'], {
            'persona_id': plan['persona_id'], 'source_email': plan['source_email'],
            'email': plan['email'], 'name': plan['name'], 'mbti': plan['mbti'],
            'anonymous_id': str(uuid.uuid4()), 'sessions': {}, 'user_id': None,
        })
        self.tags = {'run_id': campaign.args.run_id, 'persona_id': plan['persona_id'], 'scenario': 'account'}
        self.events = []
        self.tracking_errors = []
        self.active = 0
        self.seen = set()
        self.history = []

    async def route(self, route):
        request = route.request
        if urlsplit(request.url).path != '/api/v1/tracking/events' or request.method != 'POST':
            await route.continue_()
            return
        self.active += 1
        try:
            payload = request.post_data_json
            tagged = tag_events(payload['events'], dict(self.tags))
            authenticated = bool(request.headers.get('authorization'))
            append_json(self.campaign.directory / 'attempts.jsonl', {
                'persona_id': self.plan['persona_id'], 'authenticated': authenticated, 'events': tagged,
            })
            response = await route.fetch(post_data=json.dumps({'events': tagged}, ensure_ascii=False),
                                         max_redirects=0, timeout=20000)
            body = await response.json()
            if response.status != 202 or body.get('accepted', 0) + body.get('duplicates', 0) != len(tagged):
                self.tracking_errors.append({'status': response.status, 'event_ids': [e['event_id'] for e in tagged]})
            else:
                for event in tagged:
                    if event['event_id'] in self.seen:
                        continue
                    self.seen.add(event['event_id'])
                    record = {'persona_id': self.plan['persona_id'], 'authenticated': authenticated, 'event': event}
                    self.events.append(record)
                    append_json(self.campaign.directory / 'events.jsonl', record)
            await route.fulfill(response=response)
        except Exception as exc:
            self.tracking_errors.append({'error': type(exc).__name__})
            await route.abort()
        finally:
            self.active -= 1

    async def flush(self, page):
        # Flush the real tracker; do not manufacture events or bypass the UI.
        await page.evaluate("""async () => {
            const { tracker } = await import('/src/utils/tracker.js');
            await tracker.flush();
        }""")
        await page.evaluate(DRAIN_TRACKING)
        for _ in range(250):
            if not self.active:
                break
            await asyncio.sleep(0.1)
        if self.active or self.tracking_errors:
            raise RuntimeError(f'Tracking did not acknowledge all events: {self.tracking_errors}')

    async def home(self, page):
        await page.goto(self.campaign.args.base_url, wait_until='domcontentloaded')
        await page.locator('.show-card').first.wait_for()

    async def login(self, page):
        from playwright.async_api import expect
        await page.goto(self.campaign.args.base_url + '/login', wait_until='domcontentloaded')
        await page.locator('input[name=email]').fill(self.plan['email'])
        await page.locator('input[name=password]').fill(self.campaign.state['password'])
        async with page.expect_response(lambda r: urlsplit(r.url).path == '/api/v1/auth/login') as pending:
            await page.locator('form').get_by_role('button', name='로그인', exact=True).click()
        response = await pending.value
        if response.status != 200:
            raise RuntimeError(f'Login failed ({response.status}); existing account will not be overwritten')
        user = (await response.json())['user']
        if user['name'] != self.plan['name'] or user['mbti'] != self.plan['mbti'] or not user['consent']:
            raise RuntimeError('Existing test account does not match the persona')
        if self.account['user_id'] and self.account['user_id'] != user['id']:
            raise RuntimeError('Mapped account identity changed')
        self.account['user_id'] = user['id']
        self.campaign.save()
        await expect(page.get_by_role('button', name='로그아웃', exact=True)).to_be_visible()
        await page.locator('.show-card').first.wait_for()

    async def signup(self, page):
        from playwright.async_api import expect
        await page.goto(self.campaign.args.base_url + '/signup', wait_until='domcontentloaded')
        for field, value in [('nickname', self.plan['name']), ('email', self.plan['email']),
                             ('password', self.campaign.state['password']),
                             ('passwordConfirm', self.campaign.state['password'])]:
            await page.locator(f'input[name={field}]').fill(value)
        await page.get_by_role('radio', name=self.plan['mbti'], exact=True).check()
        await page.locator('input[name=consent]').check()
        async with page.expect_response(lambda r: urlsplit(r.url).path == '/api/v1/auth/signup') as pending:
            await page.get_by_role('button', name='동의하고 시작하기').click()
        response = await pending.value
        if response.status == 409:
            await self.login(page)
            return
        if response.status != 201:
            raise RuntimeError(f'Signup failed: HTTP {response.status}')
        user = (await response.json())['user']
        self.account['user_id'] = user['id']
        self.account['created_by_run'] = True
        self.campaign.save()
        await expect(page.get_by_role('button', name='로그아웃', exact=True)).to_be_visible()
        await self.flush(page)
        await page.get_by_role('button', name='로그아웃', exact=True).click()
        await self.flush(page)

    async def visit(self, page, session, record):
        from playwright.async_api import expect
        rng = random.Random(session['selection_seed'])
        await self.login(page)
        # Each session begins at the unfiltered home; wait for its category response.
        category = session['category']
        async with page.expect_response(lambda r: urlsplit(r.url).path == '/api/v1/performances'
                                         and parse_qs(urlsplit(r.url).query).get('category') == [category]) as pending:
            await page.get_by_role('button', name=category, exact=True).first.click()
        if (await pending.value).status != 200:
            raise RuntimeError('Category list failed')
        await expect(page.locator('.show-card').first).to_be_visible()
        expand = page.get_by_role('button', name='더 많은 설렘 만나보기 ＋', exact=True)
        if await expand.count():
            await expand.click()
        buttons = page.locator('.show-card .poster-button')
        await buttons.first.wait_for()
        labels = await buttons.evaluate_all('(nodes) => nodes.map(n => n.getAttribute("aria-label"))')
        if not labels:
            raise RuntimeError('No performances in selected category')
        for index in range(session['views']):
            familiar = [label for label in labels if label in self.history]
            unseen = [label for label in labels if label not in self.history]
            if familiar and rng.random() < session['revisit_probability']:
                label = rng.choice(familiar)
            else:
                label = rng.choice(unseen or labels)
            self.history.append(label)
            title = label.removesuffix(' 상세 및 예매')
            last = index == session['views'] - 1
            if last and session['outcome'] != 'view_only':
                favorite = page.get_by_role('button', name=title + ' 찜하기', exact=True)
                if await favorite.count():
                    async with page.expect_response(lambda r: r.request.method == 'PUT'
                                                     and '/api/v1/favorites/' in r.url) as pending:
                        await favorite.click()
                    if (await pending.value).status != 204:
                        raise RuntimeError('Favorite was not saved')
            async with page.expect_response(lambda r: r.request.method == 'GET'
                                             and urlsplit(r.url).path.startswith('/api/v1/performances/')
                                             and not urlsplit(r.url).path.endswith('/ranking')) as pending:
                await page.get_by_role('button', name=label, exact=True).click()
            detail_response = await pending.value
            if detail_response.status != 200:
                raise RuntimeError('Performance detail failed')
            show = await detail_response.json()
            if show['category'] != category:
                raise RuntimeError('Selected performance category differs from plan')
            record['views'].append({'performance_id': show['id'], 'category': show['category']})
            if last and session['outcome'] != 'view_only':
                record['favorite_ids'].append(show['id'])
            dialog = page.get_by_role('dialog')
            await expect(dialog).to_be_visible()
            await page.wait_for_timeout(rng.randint(100, 350))
            if not last or session['outcome'] in ('view_only', 'favorite_only'):
                await dialog.get_by_role('button', name='창 닫기', exact=True).click()
                continue
            future = [i for i, value in enumerate(show['available_dates']) if value >= date.today().isoformat()]
            if not future:
                raise RuntimeError('Selected show has no future dates')
            await dialog.locator('.date-option').nth(rng.choice(future)).click()
            await dialog.locator('.slot-option').nth(rng.randrange(len(show['slots']))).click()
            await dialog.get_by_label('예매 수량').select_option(str(session['quantity']))
            await dialog.get_by_role('button', name='예매하기', exact=True).click()
            await expect(dialog.get_by_role('heading', name='예매 확인', exact=True)).to_be_visible()
            if session['outcome'] == 'booking_abandon':
                await dialog.get_by_role('button', name='창 닫기', exact=True).click()
                continue
            await dialog.get_by_role('checkbox').check()
            async with page.expect_response(lambda r: r.request.method == 'POST'
                                             and urlsplit(r.url).path == '/api/v1/reservations') as pending:
                await dialog.get_by_role('button', name=re.compile(r'^예매하기 ·')).click()
            response = await pending.value
            if response.status != 201:
                raise RuntimeError(f'Reservation failed: HTTP {response.status}')
            reservation = await response.json()
            record['reservations'].append({'id': reservation['id'], 'performance_id': show['id'],
                                           'payment_status': 'PENDING', 'quantity': session['quantity']})
            self.campaign.save()  # Persist the ID before the next side effect.
            if session['outcome'] == 'purchase':
                async with page.expect_response(lambda r: r.request.method == 'POST'
                                                 and urlsplit(r.url).path.endswith('/complete')) as pending:
                    await dialog.get_by_role('button', name=re.compile(r'^[\d,]+원 결제하기$')).click()
                response = await pending.value
                if response.status != 200 or (await response.json())['payment_status'] != 'COMPLETED':
                    raise RuntimeError('Mock payment did not complete')
                record['reservations'][-1]['payment_status'] = 'COMPLETED'
                self.campaign.save()
                await expect(dialog.get_by_text('결제 완료', exact=True)).to_be_visible()
            await dialog.get_by_role('button', name='창 닫기', exact=True).click()
        await self.flush(page)

    async def run(self, browser):
        pending_sessions = [s for s in self.plan['sessions']
                            if session_pending(self.account['sessions'].get(str(s['index'])))]
        if not pending_sessions:
            return
        context = await browser.new_context(user_agent=f'TikitSynthetic/1.0 run={self.campaign.args.run_id}',
                                            extra_http_headers={'X-Tikit-Simulation-Key': self.campaign.server['key']},
                                            viewport={'width': 1280, 'height': 900})
        await context.add_init_script('localStorage.setItem("tikit.anonymousId", ' + json.dumps(self.account['anonymous_id']) + ');')
        await context.add_init_script(OBSERVE_TRACKING)
        await context.route('**/api/v1/tracking/events', self.route)
        page = await context.new_page()
        page.set_default_timeout(20000)
        current = None
        try:
            if not self.account['user_id']:
                await self.signup(page)
                await page.close()
            else:
                await page.close()
            for session in pending_sessions:
                self.tags['scenario'] = session['outcome']
                page = await context.new_page()  # Fresh tab gives a fresh session_id.
                current = {'status': 'in_progress', 'plan': session, 'views': [],
                           'favorite_ids': [], 'reservations': [], 'event_ids': []}
                self.account['sessions'][str(session['index'])] = current
                self.campaign.save()
                start = len(self.events)
                await self.visit(page, session, current)
                await page.get_by_role('button', name='로그아웃', exact=True).click()
                await self.flush(page)
                current['event_ids'] = [r['event']['event_id'] for r in self.events[start:]]
                observed = [r['event'] for r in self.events[start:]]
                current['session_id'] = observed[0]['session_id'] if observed else None
                evidence_errors = visit_errors(current, observed)
                if evidence_errors:
                    raise RuntimeError('Visit evidence incomplete: ' + '; '.join(evidence_errors))
                current['status'] = 'complete'
                self.campaign.save()
                if self.campaign.args.count <= 3:
                    await page.screenshot(path=str(self.campaign.directory / f'{self.plan["email"].split("@")[0]}-{session["index"]}.png'))
                print(f'{self.plan["email"]} visit={session["index"] + 1} {session["outcome"]}: '
                      f'{len(current["views"])} views, {len(current["reservations"])} reservations, '
                      f'{len(current["event_ids"])} events', flush=True)
                await page.close()
        except Exception as exc:
            if current is not None:
                current['status'] = 'failed'
                current['error_type'] = type(exc).__name__
            self.account['error'] = safe_message(exc, self.campaign.state['password'])
            self.campaign.save()
            if not page.is_closed():
                await page.screenshot(path=str(self.campaign.directory / f'failure-{self.plan["persona_id"]}.png'))
            raise RuntimeError(self.account['error']) from None
        finally:
            await context.close()


async def execute(args):
    campaign = Campaign(args)
    campaign.check_pilot()
    if args.plan_only:
        save_json(campaign.directory / 'plan.json', campaign.plans)
        print(f'Wrote deterministic plan for {len(campaign.plans)} profiles; no browser actions')
        return
    from playwright.async_api import async_playwright
    campaign.check_server()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not args.headed)
        async def worker(plan):
            await UserBrowser(campaign, plan).run(browser)
        try:
            # Finish in-flight users before returning an error; never close their browser mid-payment.
            results = await run_bounded(campaign.plans[:args.count], worker, args.workers)
            errors = [str(value) for value in results if isinstance(value, BaseException)]
            if errors:
                raise RuntimeError(f'{len(errors)} users failed; inspect state.json. First: {errors[0]}')
        finally:
            await browser.close()
    completed = [s for a in campaign.state['accounts'].values() for s in a['sessions'].values() if s['status'] == 'complete']
    summary = {'run_id': args.run_id, 'requested_users': args.count,
               'completed_users': sum(all(s['status'] == 'complete' for s in a['sessions'].values())
                                      and len(a['sessions']) > 0 for a in campaign.state['accounts'].values()),
               'completed_sessions': len(completed), 'outcomes': dict(Counter(s['plan']['outcome'] for s in completed)),
               'views': sum(len(s['views']) for s in completed),
               'reservations': sum(len(s['reservations']) for s in completed),
               'payments_completed': sum(r['payment_status'] == 'COMPLETED' for s in completed for r in s['reservations'])}
    save_json(campaign.directory / f'summary-{args.count}.json', summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--base-url', default='http://127.0.0.1:5174')
    parser.add_argument('--count', type=int, choices=range(1, 101), default=3)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=1)
    parser.add_argument('--headed', action='store_true')
    parser.add_argument('--plan-only', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', args.run_id):
        parser.error('run-id must be 1-64 letters, digits, underscores or hyphens')
    args.base_url = args.base_url.rstrip('/')
    url = urlsplit(args.base_url)
    if url.scheme != 'http' or url.hostname not in ('127.0.0.1', 'localhost') or url.path or url.query:
        parser.error('Use a local HTTP frontend origin')
    asyncio.run(execute(args))


if __name__ == '__main__':
    main()
