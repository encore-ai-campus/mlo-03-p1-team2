// 여러 화면에서 쓰는 상수와 작은 도우미 함수
export const CATEGORIES = ['전체', '콘서트', '뮤지컬', '스포츠', '전시', '클래식', '연극'];
export const MBTIS = ['INTJ', 'INTP', 'ENTJ', 'ENTP', 'INFJ', 'INFP', 'ENFJ', 'ENFP', 'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ', 'ISTP', 'ISFP', 'ESTP', 'ESFP'];

export const won = n => `${Number(n).toLocaleString('ko-KR')}원`;
export const photo = (id, width = 600) => `https://images.unsplash.com/${encodeURIComponent(id)}?auto=format&fit=crop&w=${width}&q=80`;

export function formatDate(iso) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '-' : `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`;
}

// 로그인 후 돌아갈 주소는 같은 사이트 안의 경로만 허용합니다 (외부 사이트로의 리다이렉트 방지).
export function safeNext(raw) {
  if (!raw || typeof raw !== 'string') return '/';
  try {
    const url = new URL(raw, location.origin);
    if (url.origin !== location.origin) return '/';
    return url.pathname + url.search + url.hash;
  } catch {
    return '/';
  }
}

// 로그인·회원가입 화면으로 보낼 때 쓰는 경로. next에는 로그인 후 돌아올 주소를 담습니다.
export const loginRoute = next => ({ name: 'login', query: next ? { next } : {} });
export const signupRoute = next => ({ name: 'signup', query: next ? { next } : {} });

// sessionStorage는 사생활 보호 모드 등에서 막힐 수 있어 항상 try로 감쌉니다.
export const session = {
  get(key) { try { return sessionStorage.getItem(key); } catch { return null; } },
  set(key, value) { try { sessionStorage.setItem(key, value); } catch { /* 저장 불가 시 무시 */ } },
  remove(key) { try { sessionStorage.removeItem(key); } catch { /* 무시 */ } },
  take(key) { const v = this.get(key); if (v !== null) this.remove(key); return v; },
};

export const PENDING_BOOKING_KEY = 'tikit.pendingBooking';

/* ---------- 예매(reservations) ---------- */
export const PREMIUM_SURCHARGE = 30000;
export const MAX_QUANTITY = 4;
export const MAX_PERFORMANCE_PRICE = Math.floor(2147483647 / MAX_QUANTITY) - PREMIUM_SURCHARGE;
export const RESERVATION_LABELS = { REQUESTED: '예매 요청', CONFIRMED: '예매 완료', CANCELLED: '예매 취소' };
export const PAYMENT_LABELS = { PENDING: '결제 대기', COMPLETED: '결제 완료', CANCELLED: '결제 취소' };
export const seatLabel = grade => (grade === 'PREMIUM' ? '프리미엄석' : '일반석');
export const orderNumber = id => String(id).slice(0, 8).toUpperCase();

// 서버 시각(UTC)을 한국 시간으로 분 단위까지 표시합니다.
export const koreanTime = iso => new Date(iso).toLocaleString('ko-KR', {
  timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hour12: false,
});

// 예매 요청 키(UUID). 같은 키로 다시 보내면 서버가 기존 예매를 돌려주어 중복 예매를 막습니다.
export function newRequestKey() {
  if (globalThis.crypto?.randomUUID) return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40; b[8] = (b[8] & 0x3f) | 0x80;
  const h = [...b].map(x => x.toString(16).padStart(2, '0')).join('');
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}
