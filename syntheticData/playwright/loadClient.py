"""Measured API calls with durable, pessimistic write accounting."""
import json
import time

import httpx


class ApiFailure(RuntimeError):
    pass


class Api:
    def __init__(self, client, base, budget, metrics, log):
        self.client, self.base, self.budget = client, base.rstrip('/'), budget
        self.metrics, self.log = metrics, log
        self.epoch = time.monotonic()
        self.stage = 'preparation'
        self.inflight = 0
        self.should_stop = lambda: False

    async def call(self, method, path, *, token=None, payload=None, total=0,
                   tracking=0, expected=(200,), label=None):
        if self.should_stop():
            raise ApiFailure('Run is stopping; no new API call admitted')
        ticket = self.budget.reserve(total, tracking) if total else None
        start = time.monotonic()
        status, ok = 0, False
        self.inflight += 1
        try:
            response = await self.client.request(method, self.base + '/api/v1' + path,
                          headers={'Authorization': 'Bearer ' + token} if token else {}, json=payload)
            status = response.status_code
            if status not in expected:
                raise ApiFailure(f'{method} {label or path}: HTTP {status}')
            data = None if status == 204 else response.json()
            actual_total, actual_tracking = total, tracking
            if status == 409 and 409 in expected:
                actual_total = actual_tracking = 0
            if tracking:
                accepted, duplicates = data.get('accepted'), data.get('duplicates')
                if (type(accepted) is not int or type(duplicates) is not int or
                        min(accepted, duplicates) < 0 or accepted + duplicates != len(payload['events'])):
                    raise ApiFailure('Invalid tracking acknowledgement')
                actual_total = actual_tracking = accepted
            if ticket:
                self.budget.settle(ticket, actual_total, actual_tracking)
            ok = True
            return data
        except (httpx.HTTPError, ValueError) as exc:
            raise ApiFailure(f'{method} {label or path}: {type(exc).__name__}') from None
        finally:
            self.inflight -= 1
            row = self.metrics.add(time.monotonic() - self.epoch, method + ' ' + (label or path),
                                   (time.monotonic() - start) * 1000, ok,
                                   'read' if method == 'GET' else 'write')
            row.update(stage=self.stage, status=status)
            with self.log.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(row) + '\n')
