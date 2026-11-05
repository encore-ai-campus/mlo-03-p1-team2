import { MAX_PERFORMANCE_PRICE } from '@/utils';

// 백엔드 API 호출 공통 처리: JSON 요청/응답, 토큰 헤더, 오류 메시지 변환
// API 주소는 같은 출처의 /api/v1 (개발: Vite 프록시, 배포: nginx 프록시).
// 프록시 없이 직접 연결할 때만 .env 파일에 VITE_API_BASE=http://localhost:8000/api/v1 을 지정합니다.
const base = (import.meta.env.VITE_API_BASE || '/api/v1').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, status) { super(message); this.name = 'ApiError'; this.status = status; }
}

// FastAPI 422 검증 오류(detail 배열)를 화면에 보여줄 한국어 문장으로 바꿉니다.
const fieldMessages = {
  name: '닉네임은 1~30자로 입력해 주세요.',
  email: '올바른 이메일 주소를 입력해 주세요.',
  password: '비밀번호는 8~128자로 입력해 주세요.',
  password_confirm: '비밀번호 확인을 입력해 주세요.',
  mbti: 'MBTI를 선택해 주세요.',
  consent: '개인정보 수집에 동의해 주세요.',
  current_password: '현재 비밀번호를 확인해 주세요.',
  new_password: '새 비밀번호는 8~128자로 입력해 주세요.',
  new_password_confirm: '새 비밀번호 확인을 입력해 주세요.',
  title: '공연명은 1~200자로 입력해 주세요.',
  category: '공연 카테고리를 선택해 주세요.',
  venue: '공연장은 1~200자로 입력해 주세요.',
  start_date: '올바른 공연 시작일을 입력해 주세요.',
  end_date: '올바른 공연 종료일을 입력해 주세요.',
  price: `가격은 0~${MAX_PERFORMANCE_PRICE.toLocaleString('ko-KR')}원 사이의 정수로 입력해 주세요.`,
  slots: '회차는 1개 이상, 최대 24개까지 입력해 주세요.',
  image: '올바른 포스터 이미지 주소를 입력해 주세요.',
  english: '포스터 제목은 200자 이내로 입력해 주세요.',
  sub: '포스터 부제는 200자 이내로 입력해 주세요.',
  badge: '포스터 배지는 100자 이내로 입력해 주세요.',
  tag: '목록 태그는 100자 이내로 입력해 주세요.',
};

function validationMessage(detail) {
  const first = detail[0] || {};
  const msg = String(first.msg || '');
  // 서버의 ValueError 메시지(한국어)는 "Value error, " 접두어를 떼고 그대로 사용
  if (msg.startsWith('Value error, ')) return msg.slice('Value error, '.length);
  const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : '';
  return fieldMessages[field] || '입력한 내용을 다시 확인해 주세요.';
}

export async function request(path, { method = 'GET', body, token } = {}) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(`${base}${path}`, {
      method, headers, body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError('서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.', 0);
  }

  if (response.status === 204) return null;
  let data = null;
  try { data = await response.json(); } catch { /* 본문이 JSON이 아닌 경우 */ }

  if (!response.ok) {
    const detail = data && data.detail;
    let message;
    if (typeof detail === 'string') message = detail;
    else if (Array.isArray(detail)) message = validationMessage(detail);
    else if (response.status >= 500) message = '서버에 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.';
    else message = '요청을 처리하지 못했습니다.';
    throw new ApiError(message, response.status);
  }
  return data;
}
