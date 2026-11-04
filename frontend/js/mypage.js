'use strict';
// 마이페이지: 왼쪽 메뉴 + 오른쪽 내용. 주소의 #해시(#profile, #password, #orders …)로 메뉴를 전환합니다.
// 새 기능을 붙일 때는 MENU에서 해당 항목의 soon을 지우고 render 함수를 연결하면 됩니다.

let profile = null;

const MENU = [
  { group: '나의 계정', items: [
    { id: 'profile', label: '회원 정보 수정', render: renderProfile },
    { id: 'password', label: '비밀번호 변경', render: renderPassword },
  ] },
  { group: '나의 티켓', items: [
    { id: 'orders', label: '예매 내역', soon: '예매한 공연의 관람 일시·좌석·결제 정보를 한눈에 확인하고 관리할 수 있어요.' },
    { id: 'refunds', label: '취소·환불 내역', soon: '예매 취소 신청과 환불 진행 상황을 확인할 수 있어요.' },
    { id: 'favorites', label: '찜한 공연', soon: '하트로 담아 둔 공연을 모아 보고 바로 예매할 수 있어요.' },
  ] },
  { group: '나의 취향', items: [
    { id: 'taste', label: 'MBTI 취향 리포트', soon: '나의 관람 기록과 같은 MBTI 사용자의 취향을 분석해 보여드려요.' },
  ] },
  { group: '설정', items: [
    { id: 'notifications', label: '알림 설정', soon: '티켓 오픈·관람일 알림을 받을 방법을 선택할 수 있어요.' },
    { id: 'withdraw', label: '회원 탈퇴', soon: '계정과 연결된 모든 데이터를 삭제하고 탈퇴할 수 있어요.' },
  ] },
];
const ITEMS = MENU.flatMap(g => g.items);
const DEFAULT_TAB = 'profile';

/* ---------- 공통 ---------- */
const api = (path, options = {}) => tikitApi.request(path, { ...options, token: tikitAuth.token() });

async function authed(path, options = {}) {
  try {
    return await api(path, options);
  } catch (err) {
    if (err.status === 401) {
      tikitAuth.logout();
      goLogin(`mypage.html${location.hash}`);
    }
    throw err;
  }
}

function renderSide() {
  $('#sideMbti').textContent = profile.mbti;
  $('#sideName').textContent = `${profile.name}님`;
  $('#sideEmail').textContent = profile.email;
  renderAccount(profile);
  // 이름 옆 링크는 마이페이지 자신이므로 그대로 둡니다.
}

function renderMenu(active) {
  $('#mypageMenu').innerHTML = MENU.map(g => `
    <p class="mypage-menu-title">${g.group}</p>
    <ul>${g.items.map(i => `<li><a href="#${i.id}" class="${i.id === active ? 'active' : ''}"${i.id === active ? ' aria-current="page"' : ''}>
      ${i.label}${i.soon ? '<span class="soon-pill">준비 중</span>' : ''}</a></li>`).join('')}</ul>`).join('');
}

function route() {
  const id = location.hash.slice(1);
  const item = ITEMS.find(i => i.id === id) || ITEMS.find(i => i.id === DEFAULT_TAB);
  renderMenu(item.id);
  if (item.soon) renderSoon(item); else item.render();
}

function panelHead(kicker, title, intro) {
  return `<div class="panel-head"><div class="section-kicker">${kicker}</div><h2>${title}</h2>${intro ? `<p class="modal-intro">${intro}</p>` : ''}</div>`;
}

/* ---------- 준비 중 메뉴 ---------- */
function renderSoon(item) {
  $('#panel').innerHTML = `${panelHead('COMING SOON', item.label)}
    <div class="soon-box">
      <div class="soon-icon">✦</div>
      <b>곧 만나볼 수 있어요</b>
      <p></p>
      <a class="secondary soon-link" href="./">공연 둘러보기 ↗</a>
    </div>`;
  $('.soon-box p').textContent = item.soon;
}

/* ---------- 회원 정보 수정 ---------- */
function renderProfile() {
  $('#panel').innerHTML = `${panelHead('ACCOUNT', '회원 정보 수정', '닉네임·이메일·MBTI를 변경할 수 있어요. 이메일을 바꾸면 다음 로그인부터 새 이메일을 사용합니다.')}
    <form id="profileForm" class="mypage-form" novalidate>
      <label class="form-field"><span>닉네임 <span class="required">*</span></span><input name="name" required maxlength="20" autocomplete="nickname"></label>
      <label class="form-field"><span>이메일 <span class="required">*</span></span><input name="email" type="email" required maxlength="100" autocomplete="email"></label>
      <div id="currentPasswordField" hidden>
        <label class="form-field"><span>현재 비밀번호 <span class="required">*</span></span><span class="password-control"><input name="currentPassword" type="password" maxlength="128" autocomplete="current-password" placeholder="이메일 변경을 위해 현재 비밀번호를 입력해 주세요"><button type="button" data-toggle-password="currentPassword" aria-label="비밀번호 표시" aria-pressed="false">보기</button></span></label>
      </div>
      <p class="field-title" id="mbtiTitle">나의 MBTI <span class="required">*</span></p>
      <div class="mbti-options" role="radiogroup" aria-labelledby="mbtiTitle">
        ${MBTIS.map(m => `<label class="mbti-option"><input type="radio" name="mbti" value="${m}"><span>${m}</span></label>`).join('')}
      </div>
      <dl class="mypage-meta">
        <div><dt>가입일</dt><dd id="metaJoined"></dd></div>
        <div><dt>정보 수집 동의</dt><dd id="metaConsent"></dd></div>
      </dl>
      <p class="form-error" role="alert" hidden></p>
      <button class="primary" type="submit">변경 내용 저장</button>
    </form>`;

  const form = $('#profileForm');
  form.elements.name.value = profile.name;
  form.elements.email.value = profile.email;
  $(`[name=mbti][value="${profile.mbti}"]`, form).checked = true;
  $('#metaJoined').textContent = formatDate(profile.created_at);
  $('#metaConsent').textContent = profile.consent ? `동의함 (${formatDate(profile.consented_at)})` : '미동의';
  attachPasswordToggles(form);

  const emailChanged = () => form.elements.email.value.trim().toLowerCase() !== profile.email;
  form.oninput = () => {
    hideFormError(form);
    $('#currentPasswordField').hidden = !emailChanged();
  };

  form.onsubmit = async e => {
    e.preventDefault();
    if (form.dataset.busy) return;
    const name = form.elements.name.value.trim();
    const email = form.elements.email.value.trim().toLowerCase();
    const mbti = new FormData(form).get('mbti');
    if (!name) { showFormError(form, '닉네임을 입력해 주세요.'); return; }
    if (!email || !form.elements.email.checkValidity()) { showFormError(form, '올바른 이메일 주소를 입력해 주세요.'); return; }

    const body = {};
    if (name !== profile.name) body.name = name;
    if (mbti && mbti !== profile.mbti) body.mbti = mbti;
    if (emailChanged()) {
      if (!form.elements.currentPassword.value) { showFormError(form, '이메일을 변경하려면 현재 비밀번호를 입력해 주세요.'); return; }
      body.email = email;
      body.current_password = form.elements.currentPassword.value;
    }
    if (!Object.keys(body).length) { showFormError(form, '변경된 내용이 없어요.'); return; }

    setBusy(form, true, '저장 중…');
    try {
      profile = await authed('/users/me', { method: 'PATCH', body });
      renderSide();
      renderProfile();
      toast('회원 정보를 변경했어요.');
    } catch (err) {
      if (form.isConnected) { showFormError(form, err.message); setBusy(form, false, '변경 내용 저장'); }
    }
  };
}

/* ---------- 비밀번호 변경 ---------- */
function renderPassword() {
  const field = (name, label, autocomplete, placeholder) =>
    `<label class="form-field"><span>${label} <span class="required">*</span></span><span class="password-control">` +
    `<input name="${name}" type="password" required maxlength="128" autocomplete="${autocomplete}" placeholder="${placeholder}">` +
    `<button type="button" data-toggle-password="${name}" aria-label="${label} 표시" aria-pressed="false">보기</button></span></label>`;

  $('#panel').innerHTML = `${panelHead('SECURITY', '비밀번호 변경', '안전을 위해 현재 비밀번호를 확인한 뒤 변경합니다.')}
    <form id="passwordForm" class="mypage-form" novalidate>
      ${field('currentPassword', '현재 비밀번호', 'current-password', '현재 비밀번호 입력')}
      ${field('newPassword', '새 비밀번호', 'new-password', '8~128자 입력')}
      ${field('newPasswordConfirm', '새 비밀번호 확인', 'new-password', '새 비밀번호를 다시 입력해 주세요')}
      <div class="demo-note">시연용 서비스입니다. 실제 사용하는 비밀번호는 입력하지 마세요.</div>
      <p class="form-error" role="alert" hidden></p>
      <button class="primary" type="submit">비밀번호 변경</button>
    </form>`;

  const form = $('#passwordForm');
  attachPasswordToggles(form);
  form.oninput = () => hideFormError(form);
  form.onsubmit = async e => {
    e.preventDefault();
    if (form.dataset.busy) return;
    const current = form.elements.currentPassword.value;
    const next = form.elements.newPassword.value;
    if (!current) { showFormError(form, '현재 비밀번호를 입력해 주세요.'); return; }
    if (next.length < 8 || next.length > 128) { showFormError(form, '새 비밀번호는 8~128자로 입력해 주세요.'); return; }
    if (next !== form.elements.newPasswordConfirm.value) { showFormError(form, '새 비밀번호가 일치하지 않습니다.'); return; }
    if (next === current) { showFormError(form, '현재 비밀번호와 다른 비밀번호를 입력해 주세요.'); return; }

    setBusy(form, true, '변경 중…');
    try {
      await authed('/users/me/password', {
        method: 'PUT',
        body: { current_password: current, new_password: next, new_password_confirm: form.elements.newPasswordConfirm.value },
      });
      form.reset();
      setBusy(form, false, '비밀번호 변경');
      toast('비밀번호를 변경했어요. 다음 로그인부터 새 비밀번호를 사용해 주세요.');
    } catch (err) {
      if (form.isConnected) { showFormError(form, err.message); setBusy(form, false, '비밀번호 변경'); }
    }
  };
}

function formatDate(iso) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '-' : `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`;
}

/* ---------- 시작 ---------- */
(async () => {
  renderGenreNav();
  try {
    profile = await tikitAuth.current();
  } catch (err) {
    toast(err.message);
    return;
  }
  // 로그인하지 않았으면 로그인 페이지로 보냈다가 다시 돌아옵니다.
  if (!profile) { location.replace(loginUrl(`mypage.html${location.hash}`)); return; }
  $('#mypage').hidden = false;
  renderSide();
  route();
  window.addEventListener('hashchange', () => { route(); $('#panel').focus?.(); });
})();
