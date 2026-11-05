import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { request } from '@/api/client';
import { session } from '@/utils';
import { track, tracker } from '@/utils/tracker';

// 서버 인증: 가입·로그인 후 받은 JWT를 sessionStorage에 보관합니다.
// sessionStorage는 탭 단위라 새로고침해도 로그인이 유지되고, 탭을 닫으면 로그아웃됩니다.
// 비밀번호는 서버로만 전송하며 브라우저에는 저장하지 않습니다.
const TOKEN_KEY = 'tikit.token';

export const useAuthStore = defineStore('auth', () => {
  const token = ref(session.get(TOKEN_KEY));
  const profile = ref(null);
  let restoring = null;

  const isLoggedIn = computed(() => Boolean(profile.value));
  const isAdmin = computed(() => profile.value?.is_admin === true);

  function start(result) {
    tracker.flush(); // 로그인 전에 쌓인 이벤트는 비회원 이벤트로 먼저 보냅니다.
    token.value = result.access_token;
    session.set(TOKEN_KEY, token.value);
    profile.value = result.user;
    return result.user;
  }

  async function signup({ name, email, password, passwordConfirm, mbti, consent }) {
    const result = await request('/auth/signup', {
      method: 'POST',
      body: { name, email, password, password_confirm: passwordConfirm, mbti, consent },
    });
    const user = start(result);
    track('sign_up', { mbti: user.mbti });
    return user;
  }

  async function login(email, password) {
    const result = await request('/auth/login', { method: 'POST', body: { email, password } });
    const user = start(result);
    track('login');
    return user;
  }

  function logout() {
    tracker.flush(); // 로그아웃 전까지 쌓인 이벤트는 지금 토큰으로 보내 회원 이벤트로 남깁니다.
    token.value = null;
    profile.value = null;
    session.remove(TOKEN_KEY);
  }

  // 저장된 토큰으로 현재 사용자를 조회합니다. 만료·무효 토큰이면 지우고 null을 반환합니다.
  // 여러 화면이 동시에 불러도 요청은 한 번만 보냅니다.
  function restore() {
    if (profile.value) return Promise.resolve(profile.value);
    if (!token.value) return Promise.resolve(null);
    if (!restoring) {
      restoring = request('/users/me', { token: token.value })
        .then(user => { profile.value = user; return user; })
        .catch(error => { if (error.status === 401) { logout(); return null; } throw error; })
        .finally(() => { restoring = null; });
    }
    return restoring;
  }

  // 토큰을 붙여 API를 호출합니다.
  const api = (path, options = {}) => request(path, { ...options, token: token.value });

  return { token, profile, isLoggedIn, isAdmin, signup, login, logout, restore, api };
});
