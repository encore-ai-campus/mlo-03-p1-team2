import { request } from '@/api/client';
import { newRequestKey } from '@/utils';

// 사용자 행동 이벤트 수집기
// - track() 으로 쌓은 이벤트를 큐에 모았다가 백엔드(POST /tracking/events → MongoDB)로 보냅니다.
// - 큐에는 최대 10개까지 쌓이며, 10개가 차면 바로 보냅니다.
// - 10개가 안 돼도 3초마다 쌓인 이벤트가 있으면 보냅니다.
// - 화면을 떠날 때(탭 숨김·페이지 이동)는 남은 이벤트를 keepalive 요청으로 보냅니다.
// 이벤트 수집이 실패해도 서비스 이용에는 영향을 주지 않습니다.

// backend/app/core/config.py 의 TRACKING_EVENT_TYPES 와 같게 유지합니다.
export const EVENT_TYPES = [
  // 탐색
  'page_view', 'search', 'category_select', 'sort_change', 'list_expand', 'performance_view', 'taste_view',
  // 찜
  'favorite_add', 'favorite_remove',
  // 예매·결제
  'booking_start', 'reservation_request', 'payment_complete', 'reservation_cancel',
  // 계정
  'sign_up', 'login', 'logout', 'profile_update', 'password_change', 'notification_settings_update', 'account_withdraw',
];
export const MAX_QUEUE = 10;
export const FLUSH_INTERVAL_MS = 3000;
export const SCHEMA_VERSION = 1;

const SESSION_KEY = 'tikit.sessionId';
const ANONYMOUS_KEY = 'tikit.anonymousId';
const MAX_TEXT = 500;

// 저장소가 막힌 환경(사생활 보호 모드 등)에서는 이번 실행 동안만 쓰는 id 를 만듭니다.
function storedId(storage, key, makeId) {
  try {
    let id = storage?.getItem(key);
    if (!id) { id = makeId(); storage?.setItem(key, id); }
    return id;
  } catch {
    return makeId();
  }
}

// 서버가 받는 형태(한 단계, 짧은 값)로 props 를 정리합니다. undefined 는 뺍니다.
function cleanProps(props) {
  const out = {};
  for (const [key, value] of Object.entries(props || {})) {
    if (value === undefined) continue;
    if (value === null || typeof value === 'boolean' || (typeof value === 'number' && Number.isFinite(value))) out[key] = value;
    else out[key] = String(value).slice(0, MAX_TEXT);
  }
  return out;
}

// 네트워크 오류(0)·서버 오류(5xx)·요청 과다(429)만 다시 보냅니다. 형식 오류(4xx)는 다시 보내도 실패하므로 버립니다.
const retryable = err => !err || err.status === 0 || err.status === 429 || err.status >= 500;

/**
 * 테스트에서 시간·전송·저장소를 바꿔 끼울 수 있도록 만든 수집기 생성 함수.
 * send(events, { token, keepalive }) 는 Promise 를 돌려줘야 합니다.
 */
export function createTracker({
  send,
  getToken = () => null,
  now = () => new Date(),
  makeId = newRequestKey,
  sessionStorage: sStore = globalThis.sessionStorage,
  localStorage: lStore = globalThis.localStorage,
  initialPage = () => ({ path: globalThis.location ? location.pathname + location.search : '/', referrer: globalThis.document?.referrer || '' }),
  maxQueue = MAX_QUEUE,
  intervalMs = FLUSH_INTERVAL_MS,
} = {}) {
  let queue = [];
  let timer = null;
  let page = null;
  let sessionId = null;
  let anonymousId = null;

  const currentPage = () => (page ??= initialPage());

  // 화면 주소가 바뀌면 이후 이벤트의 page 를 바꿉니다. 직전 화면이 referrer 가 됩니다.
  function setPage(path) {
    const previous = currentPage();
    if (previous.path === path) return;
    page = { path, referrer: previous.path };
  }

  function track(type, props = {}) {
    if (!EVENT_TYPES.includes(type)) return null;
    sessionId ??= storedId(sStore, SESSION_KEY, makeId);
    anonymousId ??= storedId(lStore, ANONYMOUS_KEY, makeId);
    const { path, referrer } = currentPage();
    const event = {
      event_id: makeId(),
      type,
      occurred_at: now().toISOString(),
      session_id: sessionId,
      anonymous_id: anonymousId,
      page: { path: path.slice(0, MAX_TEXT), referrer: referrer.slice(0, MAX_TEXT) },
      props: cleanProps(props),
      schema_version: SCHEMA_VERSION,
    };
    queue.push(event);
    if (queue.length >= maxQueue) flush();
    return event;
  }

  // 큐의 이벤트를 최대 maxQueue 개씩 보냅니다. 토큰은 보내는 순간의 것을 씁니다.
  function flush({ keepalive = false } = {}) {
    if (!queue.length) return Promise.resolve();
    const batch = queue.splice(0, maxQueue);
    const token = getToken();
    return Promise.resolve()
      .then(() => send(batch, { token, keepalive }))
      .catch(err => {
        if (!retryable(err)) return;
        // 실패한 이벤트를 앞에 되돌려 놓되, 큐는 최대 maxQueue 개를 넘지 않게 오래된 것부터 버립니다.
        queue = [...batch, ...queue].slice(-maxQueue);
      });
  }

  function start() {
    if (timer === null) timer = setInterval(() => { if (queue.length) flush(); }, intervalMs);
  }
  function stop() {
    if (timer !== null) { clearInterval(timer); timer = null; }
  }

  return { track, flush, start, stop, setPage, get size() { return queue.length; } };
}

/* ---------- 앱에서 쓰는 기본 수집기 ---------- */
let tokenGetter = () => null;

export const tracker = createTracker({
  getToken: () => tokenGetter(),
  send: (events, { token, keepalive }) => request('/tracking/events', { method: 'POST', body: { events }, token, keepalive }),
});

export const track = (type, props) => tracker.track(type, props);

// main.js 에서 한 번 호출합니다: 토큰 연결, 화면 이동 기록, 3초 주기 전송, 화면을 떠날 때 전송.
export function installTracking({ router, getToken }) {
  tokenGetter = getToken;
  router.afterEach((to, from, failure) => {
    if (failure) return;
    tracker.setPage(to.fullPath);
    // 같은 화면에서 쿼리(검색어·카테고리·정렬)만 바뀌면 각 행동 이벤트로 남기고 page_view 는 남기지 않습니다.
    if (to.path !== from.path || from.matched.length === 0) track('page_view', { route: to.name ? String(to.name) : undefined });
  });
  tracker.start();
  const flushOnLeave = () => { tracker.flush({ keepalive: true }); };
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') flushOnLeave(); });
  window.addEventListener('pagehide', flushOnLeave);
}
