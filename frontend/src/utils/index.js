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
