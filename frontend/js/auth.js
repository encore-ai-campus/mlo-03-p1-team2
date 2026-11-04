'use strict';
// 서버 인증: 가입·로그인 후 받은 JWT를 sessionStorage에 보관합니다.
// sessionStorage는 탭 단위라 새로고침해도 로그인이 유지되고, 탭을 닫으면 로그아웃됩니다.
// 비밀번호는 서버로만 전송하며 브라우저에는 저장하지 않습니다.
const tikitAuth = (() => {
  const tokenKey = 'tikit.token';

  function readToken() { try { return sessionStorage.getItem(tokenKey); } catch { return null; } }
  function saveToken(token) { try { sessionStorage.setItem(tokenKey, token); } catch { /* 저장 불가 시 이번 화면에서만 유지 */ } }
  function clearToken() { try { sessionStorage.removeItem(tokenKey); } catch { /* 무시 */ } }

  let memoryToken = readToken();

  function start(result) {
    memoryToken = result.access_token;
    saveToken(memoryToken);
    return result.user;
  }

  return {
    token() { return memoryToken; },

    async signup({ name, email, password, passwordConfirm, mbti, consent }) {
      const result = await tikitApi.request('/auth/signup', {
        method: 'POST',
        body: { name, email, password, password_confirm: passwordConfirm, mbti, consent },
      });
      return start(result);
    },

    // 저장된 토큰으로 현재 사용자를 조회합니다. 만료·무효 토큰이면 지우고 null을 반환합니다.
    async current() {
      if (!memoryToken) return null;
      try {
        return await tikitApi.request('/users/me', { token: memoryToken });
      } catch (error) {
        if (error.status === 401) { this.logout(); return null; }
        throw error;
      }
    },

    logout() { memoryToken = null; clearToken(); },
  };
})();
