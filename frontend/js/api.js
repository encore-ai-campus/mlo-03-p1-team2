'use strict';
// 백엔드 API 호출 공통 처리: JSON 요청/응답, 토큰 헤더, 오류 메시지 변환
const tikitApi = (() => {
  const base = window.TIKIT_CONFIG.apiBase.replace(/\/$/, '');

  class ApiError extends Error {
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
  };
  function validationMessage(detail) {
    const first = detail[0] || {};
    const msg = String(first.msg || '');
    // 서버의 ValueError 메시지(한국어)는 "Value error, " 접두어를 떼고 그대로 사용
    if (msg.startsWith('Value error, ')) return msg.slice('Value error, '.length);
    const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : '';
    return fieldMessages[field] || '입력한 내용을 다시 확인해 주세요.';
  }

  async function request(path, { method = 'GET', body, token } = {}) {
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

  return { request, ApiError };
})();
