"""Additional visits for existing accounts, with a separate fictional time axis."""
import argparse
import asyncio
import copy
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys

from periods import build_period_plan, period_tags, randomize_period_plan
from run import Campaign, UserBrowser, HERE, PROFILES
from scenarios import check_resume, file_sha256
from safety import save_json, run_bounded, safe_message, visit_errors, retained_favorites
from transport import OBSERVE_TRACKING


class PeriodCampaign(Campaign):
    def __init__(self, args):
        self.args = args
        self.directory = HERE / 'artifacts' / args.run_id
        self.directory.mkdir(parents=True,exist_ok=True)
        self.path = self.directory / 'state.json'
        source_path = HERE / 'artifacts' / args.source_run / 'state.json'
        source = json.loads(source_path.read_text(encoding='utf-8'))
        digest = file_sha256(PROFILES)
        if source['fingerprint']['profiles_sha256'] != digest:
            raise ValueError('Source accounts do not match the current profiles')
        self.plans = build_period_plan(json.loads(PROFILES.read_text(encoding='utf-8'))['users'],
                                       args.start,args.days,args.visits,args.seed)
        if len(self.plans) != 100:
            raise ValueError('This campaign is restricted to the existing 100 personas')
        fingerprint = {'base_url':args.base_url,'profiles_sha256':digest,'seed':args.seed,
                       'collection':'simulation','generator_version':'periods-1.0',
                       'source_run':args.source_run,'source_sha256':file_sha256(source_path),
                       'period_start':args.start.isoformat(),'days':args.days,'visits_per_user':args.visits}
        if self.path.exists():
            self.state = json.loads(self.path.read_text(encoding='utf-8'))
            if self.state['fingerprint'].get('visit_policy')=='random-frequency-v1':
                fingerprint['visit_policy']='random-frequency-v1'
                fingerprint['target_visits']=len(self.plans)*args.visits
                fingerprint['plan_sha256']=file_sha256(self.directory/'plan.json')
                self.plans=json.loads((self.directory/'plan.json').read_text(encoding='utf-8'))
            check_resume(self.state,fingerprint)
        else:
            accounts = {}
            for plan in self.plans:
                account = copy.deepcopy(source['accounts'][plan['persona_id']])
                if not account.get('user_id') or account['email'] != plan['email']:
                    raise ValueError('A mapped existing account is missing')
                account['sessions'] = {}
                account['created_by_run'] = False
                account.pop('error',None)
                accounts[plan['persona_id']] = account
            self.state = {'run_id':args.run_id,'synthetic':True,'fingerprint':fingerprint,
                          'started_at':datetime.now(timezone.utc).isoformat(),
                          'password':source['password'],'accounts':accounts}
            self.plans=randomize_period_plan(json.loads(PROFILES.read_text(encoding='utf-8'))['users'],
                                             accounts,args.start,args.days,100*args.visits,args.seed)
            save_json(self.directory/'plan.json',self.plans)
            self.state['fingerprint'].update(visit_policy='random-frequency-v1',target_visits=100*args.visits,
                                            plan_sha256=file_sha256(self.directory/'plan.json'))
            self.save()

    def check_pilot(self):
        if self.args.pilot:
            return
        path = self.directory / 'verification-periods-pilot.json'
        report = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        previous=self.state.get('schedule_revision',{}).get('validated_runtime_fingerprint')
        if not report.get('passed') or report.get('fingerprint') not in (self.state['fingerprint'],previous):
            raise ValueError('Verify the existing-account 3-person/1-visit pilot first')


class PayloadRequest:
    def __init__(self, request, payload):
        self.original = request
        self.post_data_json = payload
    def __getattr__(self, name):
        return getattr(self.original,name)


class PayloadRoute:
    def __init__(self, route, payload):
        self.original = route
        self.request = PayloadRequest(route.request,payload)
    def __getattr__(self, name):
        return getattr(self.original,name)


class PeriodBrowser(UserBrowser):
    async def signup(self, page):
        raise RuntimeError('Signup is forbidden in the additional-visit campaign')

    async def visit(self, page, session, record):
        self.period_session = session
        self.real_anchor = getattr(self,'restored_anchor',None)
        self.history = self.account.setdefault('viewed_titles',[])
        await super().visit(page,session,record)

    async def route(self, route):
        try:
            payload = route.request.post_data_json
            if self.real_anchor is None:
                self.real_anchor = min(datetime.fromisoformat(e['occurred_at'].replace('Z','+00:00'))
                                       for e in payload['events'])
            transformed = {'events':period_tags(payload['events'],self.period_session,self.real_anchor)}
            await super().route(PayloadRoute(route,transformed))
        except Exception as exc:
            self.tracking_errors.append({'error':type(exc).__name__})
            await route.abort()


async def resume_interrupted(campaign):
    from playwright.async_api import async_playwright
    audit=json.loads((campaign.directory/'stopped-audit.json').read_text(encoding='utf-8'))
    if audit['state_sha256']!=file_sha256(campaign.path):raise ValueError('Fresh interrupted-visit audit required')
    campaign.check_server()
    os.chdir(campaign.directory)
    plans={p['persona_id']:p for p in campaign.plans}
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(args=['--log-file='+str(campaign.directory/'chromium.log')])
        try:
            for job in audit['jobs']:
                plan=plans[job['persona_id']]
                runner=PeriodBrowser(campaign,plan)
                record=runner.account['sessions'][job['visit']]
                original=copy.deepcopy(record)
                from run import append_json
                append_json(campaign.directory/'period-recovery-history.jsonl',{'previous_visit':original,'audit_job':job})
                executable=copy.deepcopy(record['plan'])
                executable['views']=max(1,executable['views']-len(job['views']))
                record['views']=job['views']
                record['favorite_ids']=job['retained_favorites']
                record['plan']['views']=len(job['views'])+executable['views']
                plan['sessions'][int(job['visit'])]['views']=record['plan']['views']
                runner.tags['scenario']=record['plan']['outcome']
                if job['events']:
                    runner.restored_anchor=min(datetime.fromisoformat(e['occurred_at'].replace('Z','+00:00')) for e in job['events'])
                context=await browser.new_context(user_agent=f'TikitSynthetic/1.0 run={campaign.args.run_id}',
                        extra_http_headers={'X-Tikit-Simulation-Key':campaign.server['key']})
                await context.add_init_script(OBSERVE_TRACKING)
                script='localStorage.setItem("tikit.anonymousId",'+json.dumps(runner.account['anonymous_id'])+');'
                if job['session_id']:script+='sessionStorage.setItem("tikit.sessionId",'+json.dumps(job['session_id'])+');'
                await context.add_init_script(script)
                await context.route('**/api/v1/tracking/events',runner.route)
                page=await context.new_page()
                page.set_default_timeout(20000)
                campaign.save()
                try:
                    await runner.visit(page,executable,record)
                    await page.get_by_role('button',name='로그아웃',exact=True).click()
                    await runner.flush(page)
                    observed=job['events']+[r['event'] for r in runner.events]
                    problems=visit_errors(record,observed)
                    if problems:raise ValueError('Recovery evidence mismatch: '+'; '.join(problems))
                    record['event_ids']=[e['event_id'] for e in observed]
                    record['session_id']=observed[0]['session_id']
                    record['status']='complete'
                    record['recovery_action']='resume_after_user_schedule_change'
                    record['favorite_ids']=retained_favorites(job['retained_favorites'],record['favorite_ids'])
                    campaign.save()
                    print(runner.account['email'],'interrupted visit completed without replaying an existing reservation',flush=True)
                except Exception as exc:
                    raise RuntimeError(safe_message(exc,campaign.state['password'])) from None
                finally:
                    await context.close()
        finally:
            await browser.close()
    save_json(campaign.directory/'plan.json',campaign.plans)


def change_to_random_schedule(campaign):
    if campaign.state['fingerprint'].get('visit_policy')=='random-frequency-v1':
        raise ValueError('Campaign already uses a frozen random schedule; do not reallocate it during execution')
    if any(v['status']!='complete' for a in campaign.state['accounts'].values() for v in a['sessions'].values()):
        raise ValueError('Finish audited interrupted visits before changing the schedule')
    old=copy.deepcopy(campaign.state['fingerprint'])
    users=json.loads(PROFILES.read_text(encoding='utf-8'))['users']
    plans=randomize_period_plan(users,campaign.state['accounts'],campaign.args.start,campaign.args.days,
                                100*campaign.args.visits,campaign.args.seed)
    save_json(campaign.directory/'previous-fixed-plan.json',campaign.plans)
    save_json(campaign.directory/'plan.json',plans)
    new=dict(old,visit_policy='random-frequency-v1',target_visits=100*campaign.args.visits,
             plan_sha256=file_sha256(campaign.directory/'plan.json'))
    campaign.state['fingerprint']=new
    campaign.state['schedule_revision']={'reason':'User requested variable visit counts instead of equal counts',
                                        'validated_runtime_fingerprint':old}
    campaign.save()
    baseline=json.loads((campaign.directory/'period-baseline.json').read_text(encoding='utf-8'))
    baseline['fingerprint']=new
    save_json(campaign.directory/'period-baseline.json',baseline)
    counts=[len(p['sessions']) for p in plans]
    save_json(campaign.directory/'random-visit-allocation.json',{'counts':{p['persona_id']:len(p['sessions']) for p in plans},
              'total':sum(counts),'min':min(counts),'max':max(counts),'preserved_existing_visits':True})
    print(json.dumps({'random_schedule_ready':True,'users':len(plans),'total_visits':sum(counts),'min':min(counts),'max':max(counts)}))


async def execute_periods(args):
    campaign = PeriodCampaign(args)
    if args.resume_interrupted:
        await resume_interrupted(campaign)
        return
    if args.randomize:
        change_to_random_schedule(campaign)
        return
    if args.plan_only:
        save_json(campaign.directory / 'plan.json',campaign.plans)
        print(f'Prepared {len(campaign.plans)} existing accounts x {args.visits} additional visits; no service writes')
        return
    baseline = campaign.directory / 'period-baseline.json'
    if not baseline.exists():
        raise ValueError('Run verify_periods.py --baseline before browser actions')
    campaign.check_pilot()
    campaign.check_server()
    from playwright.async_api import async_playwright
    plans = copy.deepcopy(campaign.plans[:3] if args.pilot else campaign.plans)
    if args.pilot:
        for plan in plans:
            plan['sessions'] = plan['sessions'][:1]
    # Chromium diagnostics must stay in ignored artifacts, not the repository root.
    os.chdir(campaign.directory)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True,args=['--log-file='+str(campaign.directory/'chromium.log')])
        try:
            async def worker(plan):
                await PeriodBrowser(campaign,plan).run(browser)
            results = await run_bounded(plans,worker,args.workers)
            errors = [safe_message(r,campaign.state['password']) for r in results if isinstance(r,BaseException)]
            if errors:
                raise RuntimeError(f'{len(errors)} users failed. First: {errors[0]}')
        finally:
            await browser.close()
    completed = [s for a in campaign.state['accounts'].values() for s in a['sessions'].values() if s['status']=='complete']
    summary = {'run_id':args.run_id,'pilot':args.pilot,'new_accounts':0,
               'completed_visits':len(completed),'planned_visits':100*args.visits,
               'views':sum(len(s['views']) for s in completed),
               'reservations':sum(len(s['reservations']) for s in completed),
               'payments':sum(r['payment_status']=='COMPLETED' for s in completed for r in s['reservations'])}
    save_json(campaign.directory / ('period-summary-pilot.json' if args.pilot else 'period-summary.json'),summary)
    print(json.dumps(summary),flush=True)


def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--source-run',default='persona-20261106')
    parser.add_argument('--base-url',default='http://127.0.0.1:5174')
    parser.add_argument('--start',type=date.fromisoformat,default=date.today()-timedelta(days=29))
    parser.add_argument('--days',type=int,default=30)
    parser.add_argument('--visits',type=int,default=10)
    parser.add_argument('--seed',type=int,default=99)
    parser.add_argument('--workers',type=int,choices=range(1,5),default=4)
    parser.add_argument('--pilot',action='store_true')
    parser.add_argument('--plan-only',action='store_true')
    parser.add_argument('--resume-interrupted',action='store_true')
    parser.add_argument('--randomize',action='store_true')
    args = parser.parse_args()
    args.count = 3 if args.pilot else 100
    args.base_url = args.base_url.rstrip('/')
    if args.base_url != 'http://127.0.0.1:5174':
        parser.error('Use the guarded local simulation frontend on port 5174')
    if args.run_id == args.source_run or any(not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',v) for v in (args.run_id,args.source_run)):
        parser.error('Use distinct, valid source and new run IDs')
    asyncio.run(execute_periods(args))


if __name__=='__main__':
    main()
