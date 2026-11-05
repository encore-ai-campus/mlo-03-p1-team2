import assert from 'node:assert/strict';
import { after, mock, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

const server = await createServer({
  configFile: false,
  optimizeDeps: { noDiscovery: true, include: [] },
  resolve: { alias: { '@': fileURLToPath(new URL('../src', import.meta.url)) } },
  server: { middlewareMode: true },
  appType: 'custom',
});
after(() => server.close());
const { createTracker, MAX_QUEUE, FLUSH_INTERVAL_MS } = await server.ssrLoadModule('/src/utils/tracker.js');

const memoryStorage = () => {
  const data = new Map();
  return { getItem: k => data.get(k) ?? null, setItem: (k, v) => data.set(k, String(v)) };
};
const tick = () => new Promise(resolve => setImmediate(resolve));

function setup({ send, token = null } = {}) {
  let n = 0;
  const sent = [];
  const tracker = createTracker({
    send: send || ((events, opts) => { sent.push({ events, ...opts }); return Promise.resolve(); }),
    getToken: () => token,
    now: () => new Date('2026-11-04T05:29:44.172Z'),
    makeId: () => `00000000-0000-4000-8000-${String(++n).padStart(12, '0')}`,
    sessionStorage: memoryStorage(),
    localStorage: memoryStorage(),
    initialPage: () => ({ path: '/', referrer: '' }),
  });
  return { tracker, sent };
}

test('events have the collection schema and reuse session/anonymous ids', () => {
  const { tracker } = setup();
  const a = tracker.track('performance_view', { performance_id: 'opera', price_krw: 80000, skip: undefined, obj: { x: 1 } });
  const b = tracker.track('search', { query: '재즈' });
  assert.deepEqual(Object.keys(a).sort(), ['anonymous_id', 'event_id', 'occurred_at', 'page', 'props', 'schema_version', 'session_id', 'type']);
  assert.equal(a.occurred_at, '2026-11-04T05:29:44.172Z');
  assert.deepEqual(a.page, { path: '/', referrer: '' });
  assert.deepEqual(a.props, { performance_id: 'opera', price_krw: 80000, obj: '[object Object]' });
  assert.equal(a.schema_version, 1);
  assert.notEqual(a.event_id, b.event_id);
  assert.equal(a.session_id, b.session_id);
  assert.equal(a.anonymous_id, b.anonymous_id);
  assert.equal(tracker.track('not_a_real_type'), null);
  assert.equal(tracker.size, 2);
});

test('the queue is sent as soon as it reaches 10 events', async () => {
  const { tracker, sent } = setup({ token: 'jwt-a' });
  for (let i = 0; i < MAX_QUEUE - 1; i++) tracker.track('page_view');
  await tick();
  assert.equal(sent.length, 0);
  tracker.track('page_view');
  await tick();
  assert.equal(sent.length, 1);
  assert.equal(sent[0].events.length, MAX_QUEUE);
  assert.equal(sent[0].token, 'jwt-a');
  assert.equal(tracker.size, 0);
});

test('every 3 seconds pending events are sent, and nothing is sent when the queue is empty', async () => {
  mock.timers.enable({ apis: ['setInterval'] });
  try {
    const { tracker, sent } = setup();
    tracker.start();
    mock.timers.tick(FLUSH_INTERVAL_MS);
    await tick();
    assert.equal(sent.length, 0);

    tracker.track('login');
    tracker.track('page_view');
    mock.timers.tick(FLUSH_INTERVAL_MS - 1);
    await tick();
    assert.equal(sent.length, 0);
    mock.timers.tick(1);
    await tick();
    assert.equal(sent.length, 1);
    assert.deepEqual(sent[0].events.map(e => e.type), ['login', 'page_view']);
    tracker.stop();
  } finally {
    mock.timers.reset();
  }
});

test('network/server failures are retried, bad requests are dropped', async () => {
  let fail = { status: 0 };
  const calls = [];
  const { tracker } = setup({ send: events => { calls.push(events.length); return fail ? Promise.reject(fail) : Promise.resolve(); } });
  tracker.track('page_view');
  await tracker.flush();
  assert.equal(tracker.size, 1);

  fail = { status: 503 };
  await tracker.flush();
  assert.equal(tracker.size, 1);

  fail = { status: 422 };
  await tracker.flush();
  assert.equal(tracker.size, 0);
  assert.deepEqual(calls, [1, 1, 1]);
});

test('while the backend is down the queue never holds more than 10 events', async () => {
  const { tracker } = setup({ send: () => Promise.reject({ status: 0 }) });
  for (let i = 0; i < 25; i++) tracker.track('page_view');
  await tick();
  await tracker.flush();
  assert.ok(tracker.size <= MAX_QUEUE, `size=${tracker.size}`);
});

test('setPage updates path and referrer of later events', () => {
  const { tracker } = setup();
  tracker.setPage('/mypage/orders');
  const e = tracker.track('page_view');
  assert.deepEqual(e.page, { path: '/mypage/orders', referrer: '/' });
});

test('flush passes keepalive for page-leave sends', async () => {
  const { tracker, sent } = setup();
  tracker.track('logout');
  await tracker.flush({ keepalive: true });
  assert.equal(sent[0].keepalive, true);
});
