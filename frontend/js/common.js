'use strict';
// 모든 페이지 공통: DOM 도우미, 토스트, 헤더(카테고리 메뉴·계정 영역), 로그인 페이지 이동
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const CATEGORIES = ['전체', '콘서트', '뮤지컬', '스포츠', '전시', '클래식', '연극'];
const MBTIS = ['INTJ','INTP','ENTJ','ENTP','INFJ','INFP','ENFJ','ENFP','ISTJ','ISFJ','ESTJ','ESFJ','ISTP','ISFP','ESTP','ESFP'];

const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const won = n => `${Number(n).toLocaleString('ko-KR')}원`;
const photo = (id, width = 600) => `https://images.unsplash.com/${encodeURIComponent(id)}?auto=format&fit=crop&w=${width}&q=80`;

function toast(message) {
  const el = $('#toast');
  if (!el) return;
  el.textContent = message;
  el.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove('show'), 3200);
}

/* ---------- 페이지 이동 ---------- */
// 로그인 후 돌아갈 주소는 같은 사이트 안의 경로만 허용합니다 (외부 사이트로의 리다이렉트 방지).
function safeNext(raw) {
  if (!raw) return './';
  try {
    const url = new URL(raw, location.origin);
    if (url.origin !== location.origin) return './';
    return url.pathname + url.search + url.hash;
  } catch {
    return './';
  }
}
const currentPath = () => location.pathname + location.search;
const loginUrl = (next = currentPath()) => `login.html?next=${encodeURIComponent(next)}`;
const signupUrl = (next = currentPath()) => `signup.html?next=${encodeURIComponent(next)}`;
function goLogin(next) { location.href = loginUrl(next); }

/* ---------- 헤더 ---------- */
const ticketIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v5a2 2 0 0 0 0 4v5H4v-5a2 2 0 0 0 0-4Z"/><path d="M15 5v3m0 3v2m0 3v3"/></svg>';

// 카테고리 메뉴는 링크라서 로그인·회원가입 페이지에서도 누르면 메인의 해당 카테고리로 이동합니다.
function renderGenreNav(active = '') {
  const nav = $('#genreNav');
  if (!nav) return;
  nav.innerHTML = CATEGORIES.map(c => {
    const href = c === '전체' ? './' : `./?category=${encodeURIComponent(c)}`;
    return `<a href="${href}" data-category="${c}" class="${c === active ? 'active' : ''}"${c === active ? ' aria-current="page"' : ''}>${c === '전체' ? '홈' : c}</a>`;
  }).join('');
}

function renderAccount(profile, { onLogout } = {}) {
  const box = $('#account');
  if (!box) return;
  const myTicket = `<a href="./?open=mytikit" class="my-ticket" data-mytikit>${ticketIcon} 마이티킷</a>`;
  if (profile) {
    box.innerHTML = `<b class="account-name"></b><span></span><button type="button" id="logoutButton">로그아웃</button>${myTicket}`;
    $('.account-name', box).textContent = `${profile.name}님`;
    $('#logoutButton', box).onclick = () => {
      tikitAuth.logout();
      if (onLogout) onLogout(); else location.href = './';
      toast('로그아웃했어요.');
    };
  } else {
    // 로그인·회원가입 페이지에 있을 때는 next 값을 그대로 넘겨 원래 페이지로 돌아가게 합니다.
    const onAuthPage = /\/(login|signup)\.html$/.test(location.pathname);
    const next = onAuthPage ? safeNext(new URLSearchParams(location.search).get('next')) : currentPath();
    box.innerHTML = `<a href="${escapeHTML(loginUrl(next))}">로그인</a><span></span><a href="${escapeHTML(signupUrl(next))}">회원가입</a>${myTicket}`;
  }
}

/* ---------- 폼 공통 ---------- */
function showFormError(form, message) {
  const el = $('.form-error', form);
  el.textContent = message;
  el.hidden = false;
}
function hideFormError(form) { $('.form-error', form).hidden = true; }

function setBusy(form, busy, label) {
  const button = $('[type=submit]', form);
  if (busy) form.dataset.busy = 'true'; else delete form.dataset.busy;
  button.disabled = busy;
  button.textContent = label;
}

function attachPasswordToggles(form) {
  $$('[data-toggle-password]', form).forEach(button => {
    button.onclick = () => {
      const input = $(`[name="${button.dataset.togglePassword}"]`, form);
      const visible = input.type === 'password';
      const label = input.name === 'passwordConfirm' ? '비밀번호 확인' : '비밀번호';
      input.type = visible ? 'text' : 'password';
      button.textContent = visible ? '숨기기' : '보기';
      button.setAttribute('aria-pressed', String(visible));
      button.setAttribute('aria-label', `${label} ${visible ? '숨기기' : '표시'}`);
    };
  });
}
