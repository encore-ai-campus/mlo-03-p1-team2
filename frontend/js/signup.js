'use strict';
// 회원가입 페이지: 가입이 끝나면 자동 로그인된 상태로 next 주소(없으면 메인)로 이동합니다.
(() => {
  const next = safeNext(new URLSearchParams(location.search).get('next'));
  const form = $('#signupForm');
  const password = $('[name=password]', form);
  const confirm = $('[name=passwordConfirm]', form);

  renderGenreNav();
  renderAccount(null);
  $('#toLogin').href = loginUrl(next);
  $('#mbtiOptions').innerHTML = MBTIS.map(m =>
    `<label class="mbti-option"><input type="radio" name="mbti" value="${m}" required><span>${m}</span></label>`).join('');
  attachPasswordToggles(form);
  form.oninput = () => hideFormError(form);

  tikitAuth.current().then(user => { if (user) location.replace(next); }).catch(() => {});

  // 화면에서 먼저 확인하는 규칙 (서버도 같은 규칙으로 다시 검증합니다)
  function clientError(f) {
    if (!f.get('nickname').trim()) return '닉네임을 입력해 주세요.';
    const email = $('[name=email]', form);
    if (!email.value.trim() || !email.checkValidity()) return '올바른 이메일 주소를 입력해 주세요.';
    if (password.value.length < 8 || password.value.length > 128) return '비밀번호는 8~128자로 입력해 주세요.';
    if (password.value !== confirm.value) return '비밀번호가 일치하지 않습니다.';
    if (!f.get('mbti')) return 'MBTI를 선택해 주세요.';
    if (!f.get('consent')) return '개인정보 수집에 동의해 주세요.';
    return null;
  }

  form.onsubmit = async e => {
    e.preventDefault();
    if (form.dataset.busy) return;
    const f = new FormData(form);
    const error = clientError(f);
    if (error) { showFormError(form, error); return; }

    setBusy(form, true, '가입 중…');
    try {
      const user = await tikitAuth.signup({
        name: f.get('nickname').trim(),
        email: f.get('email').trim().toLowerCase(),
        password: password.value,
        passwordConfirm: confirm.value,
        mbti: f.get('mbti'),
        consent: true,
      });
      try { sessionStorage.setItem('tikit.flash', `${user.name}님, 가입이 완료됐어요!`); } catch { /* 무시 */ }
      location.replace(next);
    } catch (err) {
      showFormError(form, err.message);
      setBusy(form, false, '동의하고 시작하기');
    }
  };
})();
