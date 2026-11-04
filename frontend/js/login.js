'use strict';
// 로그인 페이지: 성공하면 next 주소(없으면 메인)로 이동합니다.
(() => {
  const next = safeNext(new URLSearchParams(location.search).get('next'));
  const form = $('#loginForm');

  renderGenreNav();
  renderAccount(null);
  $('#toSignup').href = signupUrl(next);
  attachPasswordToggles(form);
  form.oninput = () => hideFormError(form);

  // 이미 로그인된 탭이면 바로 돌려보냅니다.
  tikitAuth.current().then(user => { if (user) location.replace(next); }).catch(() => {});

  form.onsubmit = async e => {
    e.preventDefault();
    if (form.dataset.busy) return;
    const f = new FormData(form);
    const email = f.get('email').trim();
    const password = f.get('password');
    if (!email || !password) { showFormError(form, '이메일과 비밀번호를 입력해 주세요.'); return; }

    setBusy(form, true, '로그인 중…');
    try {
      const user = await tikitAuth.login(email, password);
      try { sessionStorage.setItem('tikit.flash', `${user.name}님, 반가워요!`); } catch { /* 무시 */ }
      location.replace(next);
    } catch (err) {
      showFormError(form, err.message);
      setBusy(form, false, '로그인');
    }
  };
})();
