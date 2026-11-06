"""Apply an audited recovery through UI; never replays a reservation or payment."""
import argparse
import asyncio
import copy
import json
import re

from run import Campaign, UserBrowser, append_json
from scenarios import file_sha256
from safety import visit_errors, safe_message, retained_favorites
from transport import OBSERVE_TRACKING


async def recover(args):
    from playwright.async_api import async_playwright
    campaign = Campaign(args)
    campaign.check_server()
    audit = json.loads((campaign.directory / 'recovery-audit.json').read_text(encoding='utf-8'))
    if audit['blocked'] or audit['state_sha256'] != file_sha256(campaign.path):
        raise ValueError('Run a fresh, unblocked read-only audit before recovery')
    events = {r['event']['event_id']: r['event'] for r in
              map(json.loads, (campaign.directory / 'events.jsonl').read_text(encoding='utf-8').splitlines())}
    plans = {p['persona_id']: p for p in campaign.plans}
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            for job in audit['jobs']:
                account = campaign.state['accounts'][job['persona_id']]
                visit = account['sessions'][job['visit']]
                # Preserve all previous evidence, even for a partially lost read-only visit.
                append_json(campaign.directory / 'recovery-history.jsonl', {'job': job, 'previous_visit': copy.deepcopy(visit)})
                if job['action'] == 'reset_unstarted':
                    del account['sessions'][job['visit']]
                    campaign.save()
                    print(job['email'], 'unstarted visit reset after reservation reconciliation', flush=True)
                    continue
                if job['action'] == 'mark_complete':
                    visit['status'] = 'complete'
                    account.pop('error', None)
                    campaign.save()
                    print(job['email'], 'complete after evidence reconciliation', flush=True)
                    continue
                old_events = [events[eid] for eid in visit['event_ids'] if eid in events]
                ids = {e['session_id'] for e in old_events}
                if len(ids) != 1:
                    raise ValueError('Cannot restore an ambiguous session')
                sid = ids.pop()
                runner = UserBrowser(campaign, plans[job['persona_id']])
                runner.tags['scenario'] = visit['plan']['outcome']
                context = await browser.new_context(
                    user_agent=f'TikitSynthetic/1.0 run={args.run_id}',
                    extra_http_headers={'X-Tikit-Simulation-Key': campaign.server['key']})
                await context.add_init_script(OBSERVE_TRACKING)
                await context.add_init_script('localStorage.setItem("tikit.anonymousId", ' + json.dumps(account['anonymous_id']) + ');'
                                              'sessionStorage.setItem("tikit.sessionId", ' + json.dumps(sid) + ');')
                await context.route('**/api/v1/tracking/events', runner.route)
                page = await context.new_page()
                page.set_default_timeout(20000)
                visit['status'] = 'in_progress'
                visit['session_id'] = sid
                campaign.save()
                try:
                    if job['action'] == 'replay_browse':
                        if visit['reservations'] or visit['plan']['outcome'] not in ('view_only', 'favorite_only', 'booking_abandon'):
                            raise ValueError('Recovery will never replay a reservation')
                        previous_favorites = list(visit['favorite_ids'])
                        visit['views'] = []
                        visit['favorite_ids'] = []
                        await runner.visit(page, visit['plan'], visit)
                        visit['favorite_ids'] = retained_favorites(previous_favorites, visit['favorite_ids'])
                    else:
                        await runner.login(page)
                    await page.get_by_role('button', name='로그아웃', exact=True).click()
                    await runner.flush(page)
                    new_events = [r['event'] for r in runner.events]
                    problems = visit_errors(visit, old_events + new_events)
                    if problems:
                        raise ValueError('Recovery evidence incomplete: ' + '; '.join(problems))
                    visit['event_ids'].extend(e['event_id'] for e in new_events)
                    visit['status'] = 'complete'
                    visit['recovery_action'] = job['action']
                    account.pop('error', None)
                    campaign.save()
                    print(job['email'], job['action'], 'verified', flush=True)
                finally:
                    await context.close()
        finally:
            await browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--base-url', default='http://127.0.0.1:5174')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', args.run_id):
        parser.error('Invalid run-id')
    try:
        asyncio.run(recover(args))
    except Exception as exc:
        from run import HERE
        state = json.loads((HERE / 'artifacts' / args.run_id / 'state.json').read_text(encoding='utf-8'))
        raise SystemExit(safe_message(exc, state['password'])) from None
