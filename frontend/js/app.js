'use strict';
// 메인 화면: 검색·카테고리 메뉴, 공연 목록, 랭킹, 예매(모달), 마이티킷
// 로그인·회원가입은 별도 페이지(login.html / signup.html)로 이동합니다.

const PREMIUM_SURCHARGE = 30000;
const PAYMENT_METHODS = ['간편결제', '신용카드', '계좌이체'];
const PENDING_BOOKING_KEY = 'tikit.pendingBooking';
const icons = {
  '콘서트': '<path d="M9 18V5l12-2v13M9 9l12-2"/><ellipse cx="6" cy="18" rx="3" ry="2.5"/><ellipse cx="18" cy="16" rx="3" ry="2.5"/>',
  '뮤지컬': '<path d="M3 4c4 2 8 2 12 0v8c0 5-6 8-6 8s-6-3-6-8Z"/><path d="m6 10 2 1m3 0 2-1M7 15q2 2 4 0M18 6l3-1v8c0 4-4 7-4 7"/>',
  '스포츠': '<circle cx="12" cy="12" r="9"/><path d="m9 9 6-1 2 5-5 4-5-4ZM12 3 9 9M21 11l-4 2M15 20l-3-3M4 16l3-3M4 7l5 2"/>',
  '전시': '<rect x="3" y="4" width="18" height="16" rx="1"/><path d="m4 17 6-6 4 4 3-3 4 4"/><circle cx="16" cy="8" r="1.5"/>',
  '클래식': '<path d="M8 5c4 3 8 1 12 3v12H3v-8c0-4 5-3 5-7ZM3 15h17M7 15v5m4-5v5m4-5v5M8 5V2"/>',
  '연극': '<path d="M4 4h16v16H4ZM4 5l8 7 8-7M4 17l5-7m11 7-5-7M12 12v8"/>',
};

const modal = $('#modal');
let returnFocus = null;

let profile = null;
let favorites = [];
let allShows = [];
let ranking = [];
let listShows = [];
let category = '전체';
let search = '';
let expanded = false;
let heroIndex = 0;
let booking = null;
let listRequest = 0;

/* ---------- API 도우미 ---------- */
const api = (path, options = {}) => tikitApi.request(path, { ...options, token: tikitAuth.token() });

// 로그인이 필요한 요청: 토큰이 만료되었으면 로그인 페이지로 보냅니다.
async function authed(path, options = {}, next) {
  try {
    return await api(path, options);
  } catch (err) {
    if (err.status === 401) {
      tikitAuth.logout();
      goLogin(next);
      throw new Error('로그인이 필요합니다.');
    }
    throw err;
  }
}

/* ---------- 모달 ---------- */
// title은 이 파일 안의 고정 문자열만 사용하고, 서버 데이터는 escapeHTML로 넣습니다.
function openModal(title, content) {
  returnFocus = document.activeElement;
  $('#modalContent').innerHTML =
    `<div class="modal-header"><h2 id="modalTitle">${title}</h2><button class="close-modal" type="button" aria-label="창 닫기" data-close>×</button></div>` +
    `<div class="modal-body">${content}</div>`;
  if (!modal.open) modal.showModal();
  modal.scrollTop = 0;
}
function closeModal() { modal.close(); }
modal.addEventListener('click', e => {
  if (e.target.closest('[data-close]')) { closeModal(); return; }
  if (e.target === modal) {
    const r = modal.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) closeModal();
  }
});
modal.addEventListener('close', () => { returnFocus?.focus?.(); });

/* ---------- 주소(URL) 상태 ---------- */
// 카테고리·검색어를 주소에 반영해 두면 로그인 후 같은 화면으로 돌아올 수 있습니다.
function syncUrl() {
  const params = new URLSearchParams();
  if (category !== '전체') params.set('category', category);
  if (search) params.set('q', search);
  const qs = params.toString();
  history.replaceState(null, '', qs ? `./?${qs}` : './');
  renderAccount(profile, { onLogout });
}

/* ---------- 공연 카드 ---------- */
function poster(s) {
  return `<div class="poster poster-${escapeHTML(s.style)}"><img src="${photo(s.image)}" alt="" loading="lazy">` +
    `<span class="poster-label">${escapeHTML(s.badge)}</span><span class="poster-eyebrow">TIKIT PRESENTS · 2026</span>` +
    `<span class="poster-title">${escapeHTML(s.english)}</span><span class="poster-sub">${escapeHTML(s.sub)}</span>` +
    `<span class="poster-date">${escapeHTML(s.date_label)} · SEOUL</span></div>`;
}

function card(s) {
  const saved = favorites.includes(s.id);
  const id = escapeHTML(s.id);
  const title = escapeHTML(s.title);
  return `<article class="show-card">` +
    `<button class="poster-button" type="button" data-show="${id}" aria-label="${title} 상세 및 예매">${poster(s)}</button>` +
    `<button class="favorite ${saved ? 'saved' : ''}" type="button" data-favorite="${id}" aria-label="${title} 찜하기" aria-pressed="${saved}">${saved ? '♥' : '♡'}</button>` +
    `<div class="show-info"><div class="tags"><span class="tag">${escapeHTML(s.tag)}</span><span class="tag neutral">${escapeHTML(s.category)}</span></div>` +
    `<button class="show-title" type="button" data-show="${id}">${title}</button>` +
    `<p>${escapeHTML(s.venue)}</p><p>${escapeHTML(s.date_label)}</p>` +
    `<div class="price-line">${won(s.price)} <small>부터</small></div></div></article>`;
}

function renderCards() {
  const visible = expanded ? listShows : listShows.slice(0, 4);
  $('#performanceGrid').innerHTML = visible.map(card).join('');
  $('#emptyState').hidden = listShows.length > 0;
  $('#moreButton').hidden = listShows.length <= 4;
  $('#moreButton').innerHTML = expanded ? '간략히 보기 <span>−</span>' : '더 많은 설렘 만나보기 <span>＋</span>';
  $('#listTitle').innerHTML = search
    ? `“${escapeHTML(search)}” 검색 결과 <span>✦</span>`
    : category === '전체' ? '지금, 가장 설레는 공연 <span>✦</span>' : `${escapeHTML(category)}, 나의 다음 설렘 <span>✦</span>`;
  $$('[data-category]').forEach(el => {
    const active = el.dataset.category === category;
    el.classList.toggle('active', active);
    if (el.tagName === 'A') { if (active) el.setAttribute('aria-current', 'page'); else el.removeAttribute('aria-current'); }
    else el.setAttribute('aria-pressed', String(active));
  });
}

// 검색·카테고리·정렬은 서버(/performances)에서 처리합니다.
async function loadList() {
  const id = ++listRequest;
  const params = new URLSearchParams({ sort: $('#sortSelect').value });
  if (category !== '전체') params.set('category', category);
  if (search) params.set('q', search);
  try {
    const result = await api(`/performances?${params}`);
    if (id !== listRequest) return; // 더 늦게 보낸 요청의 결과만 반영
    listShows = result;
    renderCards();
  } catch (err) {
    if (id === listRequest) toast(err.message);
  }
}

function chooseCategory(c, scroll = true) {
  category = CATEGORIES.includes(c) ? c : '전체';
  expanded = false;
  syncUrl();
  loadList();
  if (scroll) $('#performances').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ---------- 랭킹 ---------- */
function renderRanking(c = 'all') {
  $('#rankingGrid').innerHTML = ranking.filter(s => c === 'all' || s.category === c).slice(0, 3).map((s, i) =>
    `<button class="rank-card" type="button" data-show="${escapeHTML(s.id)}"><span class="rank-number">${i + 1}</span>` +
    `<img src="${photo(s.image, 200)}" alt="" loading="lazy"><div class="rank-copy"><small>${escapeHTML(s.category)}</small>` +
    `<b>${escapeHTML(s.title)}</b><p>${escapeHTML(s.venue)}</p></div></button>`).join('');
}

/* ---------- 히어로 배너 ---------- */
const heroSlides = [
  { id: 'city', title: '우리의 밤은<br>지금부터 <em>시작이야.</em>', sticker: 'FEEL<br>YOUR<br><span>VIBE</span><small>SEOUL · 2026</small>', cta: '페스티벌' },
  { id: 'opera', title: '오래 기다려온<br>그 무대, <em>그 전율.</em>', sticker: 'THE<br>STAGE<br><span>IS YOURS</span><small>MUSICAL · 2026</small>', cta: '뮤지컬' },
  { id: 'color', title: '일상에 새로운<br>색을 <em>더해볼까요.</em>', sticker: 'COLOR<br>YOUR<br><span>DAYS</span><small>EXHIBITION · 2026</small>', cta: '전시' },
];
function slide(delta) {
  heroIndex = (heroIndex + delta + heroSlides.length) % heroSlides.length;
  const slideInfo = heroSlides[heroIndex];
  const s = allShows.find(x => x.id === slideInfo.id);
  $('#heroTitle').innerHTML = slideInfo.title;
  $('#heroSticker').innerHTML = slideInfo.sticker;
  $('#heroBook').innerHTML = `${slideInfo.cta} 만나보기 <span>↗</span>`;
  $('#heroIndex').textContent = String(heroIndex + 1).padStart(2, '0');
  $('#slideProgress').style.width = `${((heroIndex + 1) / heroSlides.length) * 100}%`;
  if (s) {
    $('#heroDescription').innerHTML = `${escapeHTML(s.title)}<br>${escapeHTML(s.venue)} · ${escapeHTML(s.date_label)}`;
    $('#heroImage').src = photo(s.image, 1400);
    $('#heroImage').alt = `${s.title} 공연 분위기 이미지`;
  }
}

/* ---------- 찜 ---------- */
async function toggleFavorite(id) {
  if (!profile) { goLogin(); return; }
  const saved = favorites.includes(id);
  try {
    await authed(`/favorites/${encodeURIComponent(id)}`, { method: saved ? 'DELETE' : 'PUT' });
    favorites = saved ? favorites.filter(x => x !== id) : [...favorites, id];
    renderCards();
    toast(saved ? '찜한 공연에서 해제했어요.' : '좋아하는 공연에 담았어요. 마이티킷에서 확인하세요.');
  } catch (err) {
    toast(err.message);
  }
}

/* ---------- 예매 ---------- */
function weekday(iso) { return ['일', '월', '화', '수', '목', '금', '토'][new Date(`${iso}T12:00:00`).getDay()]; }
function shortDate(iso) { const [, m, d] = iso.split('-'); return `${Number(m)}.${d}`; }
const total = () => (booking.show.price + booking.premium) * booking.quantity;

function detailTop(s) {
  return `<div class="detail-top">${poster(s)}<div><span class="tag">${escapeHTML(s.category)}</span><h3>${escapeHTML(s.title)}</h3>` +
    `<p>${escapeHTML(s.venue)}</p><p>${escapeHTML(s.date_label)}</p><p>시연 공연 · 만 7세 이상 · 약 120분</p></div></div>`;
}

async function loadBooking(id, saved = {}) {
  const show = await api(`/performances/${encodeURIComponent(id)}`);
  const dates = show.available_dates;
  booking = {
    show,
    dates,
    date: dates.includes(saved.date) ? saved.date : dates[0],
    slot: show.slots.includes(saved.slot) ? saved.slot : show.slots[0],
    premium: saved.premium === PREMIUM_SURCHARGE ? PREMIUM_SURCHARGE : 0,
    quantity: [1, 2, 3, 4].includes(saved.quantity) ? saved.quantity : 1,
    paymentMethod: PAYMENT_METHODS.includes(saved.paymentMethod) ? saved.paymentMethod : PAYMENT_METHODS[0],
  };
}

async function openBooking(id) {
  try {
    await loadBooking(id);
  } catch (err) {
    toast(err.message);
    return;
  }
  // 조회 기록은 실패해도 예매 흐름에 영향을 주지 않습니다.
  api('/events', { method: 'POST', body: { performance_id: id } }).catch(() => {});
  renderBooking();
}

function selectOne(selector, attr, onPick) {
  $$(selector).forEach(b => {
    b.onclick = () => {
      onPick(b.dataset[attr]);
      $$(selector).forEach(x => { x.classList.toggle('selected', x === b); x.setAttribute('aria-pressed', String(x === b)); });
    };
  });
}

function renderBooking() {
  const s = booking.show;
  openModal('설렘을 예약하는 시간', `
    <div class="booking-steps"><span class="current">01 날짜 · 회차</span><span>──</span><span>02 모의 결제</span><span>──</span><span>03 완료</span></div>
    ${detailTop(s)}
    <p class="field-title">관람 날짜 선택</p>
    <div class="date-options">${booking.dates.map(d => `<button type="button" class="date-option ${booking.date === d ? 'selected' : ''}" data-date="${d}" aria-pressed="${booking.date === d}"><small>${weekday(d)}</small>${shortDate(d)}</button>`).join('')}</div>
    <p class="field-title">회차 선택</p>
    <div class="slot-options">${s.slots.map(t => `<button type="button" class="slot-option ${booking.slot === t ? 'selected' : ''}" data-slot="${escapeHTML(t)}" aria-pressed="${booking.slot === t}">${escapeHTML(t)}</button>`).join('')}</div>
    <div class="seat-quantity">
      <label><p class="field-title">좌석 등급</p><select id="seatSelect"><option value="0">일반석 · ${won(s.price)}</option><option value="${PREMIUM_SURCHARGE}">프리미엄석 · ${won(s.price + PREMIUM_SURCHARGE)}</option></select></label>
      <label><p class="field-title">예매 수량</p><select id="quantitySelect">${[1, 2, 3, 4].map(n => `<option value="${n}">${n}매</option>`).join('')}</select></label>
    </div>
    <div class="summary-box">
      <div class="summary-line"><span>티켓 금액</span><span id="ticketSubtotal">${won(total())}</span></div>
      <div class="summary-line"><span>예매 수수료</span><span>0원</span></div>
      <div class="summary-line total"><span>총 결제 금액</span><b id="bookingTotal">${won(total())}</b></div>
    </div>
    <button class="primary" type="button" id="goPayment">${profile ? '모의 결제로 이동 →' : '로그인 후 모의 결제로 이동 →'}</button>`);

  $('#seatSelect').value = String(booking.premium);
  $('#quantitySelect').value = String(booking.quantity);
  selectOne('[data-date]', 'date', v => { booking.date = v; });
  selectOne('[data-slot]', 'slot', v => { booking.slot = v; });
  const update = () => { $('#ticketSubtotal').textContent = won(total()); $('#bookingTotal').textContent = won(total()); };
  $('#seatSelect').onchange = e => { booking.premium = Number(e.target.value); update(); };
  $('#quantitySelect').onchange = e => { booking.quantity = Number(e.target.value); update(); };
  $('#goPayment').onclick = () => {
    if (profile) { renderPayment(); return; }
    // 로그인 페이지에 다녀와도 선택한 날짜·회차가 유지되도록 현재 탭에 잠시 보관합니다.
    try {
      sessionStorage.setItem(PENDING_BOOKING_KEY, JSON.stringify({
        showId: booking.show.id, date: booking.date, slot: booking.slot,
        premium: booking.premium, quantity: booking.quantity, paymentMethod: booking.paymentMethod,
      }));
    } catch { /* 저장 불가 시 다시 선택 */ }
    goLogin('./?resume=booking');
  };
}

function renderPayment() {
  const s = booking.show;
  openModal('모의 결제', `
    <div class="booking-steps"><span>01 날짜 · 회차</span><span>──</span><span class="current">02 모의 결제</span><span>──</span><span>03 완료</span></div>
    ${detailTop(s)}
    <div class="summary-box">
      <div class="summary-line"><span>예매자 / MBTI</span><span>${escapeHTML(profile.name)} / ${escapeHTML(profile.mbti)}</span></div>
      <div class="summary-line"><span>관람 일시</span><span>${escapeHTML(booking.date)} ${escapeHTML(booking.slot)}</span></div>
      <div class="summary-line"><span>좌석 / 수량</span><span>${booking.premium ? '프리미엄석' : '일반석'} / ${booking.quantity}매</span></div>
      <div class="summary-line total"><span>총 결제 금액</span><b>${won(total())}</b></div>
    </div>
    <p class="field-title">결제 방법</p>
    <div class="payment-options">${PAYMENT_METHODS.map(m => `<button type="button" class="payment-option ${booking.paymentMethod === m ? 'selected' : ''}" data-payment="${m}" aria-pressed="${booking.paymentMethod === m}">${m}</button>`).join('')}</div>
    <div class="demo-note">실제 결제가 발생하지 않는 모의 결제입니다.<br>카드번호·계좌번호를 입력하지 마세요. 완료 시 예매 내역이 티킷 서버에 저장됩니다.</div>
    <form id="paymentForm"><label class="check-label"><input type="checkbox" required><span>공연·날짜·회차·금액을 확인했으며 모의 예매에 동의합니다.</span></label>
      <p class="form-error" role="alert" hidden></p>
      <button class="primary" type="submit">${won(total())} 모의 결제하기</button></form>
    <button class="secondary" type="button" id="backToDates">← 날짜·회차 다시 선택</button>`);

  selectOne('[data-payment]', 'payment', v => { booking.paymentMethod = v; });
  $('#backToDates').onclick = renderBooking;
  const form = $('#paymentForm');
  form.onsubmit = async e => {
    e.preventDefault();
    if (form.dataset.busy) return;
    if (!form.reportValidity()) return;
    const label = `${won(total())} 모의 결제하기`;
    setBusy(form, true, '결제 처리 중…');
    try {
      const order = await authed('/orders', {
        method: 'POST',
        body: {
          performance_id: s.id, performance_date: booking.date, session_time: booking.slot,
          seat_grade: booking.premium ? 'PREMIUM' : 'STANDARD', quantity: booking.quantity, payment_method: booking.paymentMethod,
        },
      }, './?resume=booking');
      openModal('모의 예매 완료', `
        <div class="success"><div class="success-icon">✓</div><h3>새로운 설렘이 기다리고 있어요!</h3>
        <p>${escapeHTML(order.performance_title)}<br>${escapeHTML(order.performance_date)} ${escapeHTML(order.session_time)} · ${order.quantity}매<br>모의 결제 금액 ${won(order.amount)}</p>
        <span class="tag">실제 청구 금액 0원</span><p>예매 내역이 저장되었습니다.</p></div>
        <button class="primary" type="button" id="viewOrders">예매 내역 확인하기</button>
        <button class="secondary" type="button" data-close>다른 공연 둘러보기</button>`);
      $('#viewOrders').onclick = openOrders;
      loadRanking();
    } catch (err) {
      if (form.isConnected) { showFormError(form, err.message); setBusy(form, false, label); }
    }
  };
}

/* ---------- 마이티킷 ---------- */
async function openOrders() {
  if (!profile) { goLogin('./?open=mytikit'); return; }
  let orders;
  try {
    orders = await authed('/orders', {}, './?open=mytikit');
  } catch (err) {
    toast(err.message);
    return;
  }
  const liked = allShows.filter(s => favorites.includes(s.id));
  openModal('마이티킷', `
    <p class="modal-intro">${escapeHTML(profile.name)}님의 설레는 순간들 <span class="tag">${escapeHTML(profile.mbti)}</span></p>
    <p class="field-title">나의 예매 내역 · ${orders.length}건</p>
    ${orders.length ? orders.map(o => `<article class="order-card"><span class="order-status">모의 예매 완료 · 실제 결제 없음</span>
      <h3>${escapeHTML(o.performance_title)}</h3>
      <p>${escapeHTML(o.performance_date)} ${escapeHTML(o.session_time)} · ${escapeHTML(o.venue)}<br>${o.seat_grade === 'PREMIUM' ? '프리미엄석' : '일반석'} ${o.quantity}매 · ${won(o.amount)}</p>
      <footer><span>예매번호 ${escapeHTML(String(o.id).slice(0, 8).toUpperCase())}</span><span>${new Date(o.created_at).toLocaleDateString('ko-KR')}</span></footer></article>`).join('')
      : '<div class="demo-note">아직 예매한 공연이 없어요. 마음에 드는 공연을 골라 보세요.</div>'}
    <p class="field-title">찜한 공연 · ${liked.length}개</p>
    ${liked.map(s => `<button class="secondary" type="button" data-show="${escapeHTML(s.id)}">${escapeHTML(s.title)} ↗</button>`).join('')}
    <button class="primary" type="button" id="exportData">내 취향·예매 데이터 내려받기 (JSON)</button>
    <button class="secondary" type="button" id="deleteData">내 계정·취향·예매 데이터 삭제</button>`);

  $('#exportData').onclick = async () => {
    try {
      const payload = await authed('/users/me/export');
      const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }));
      const a = document.createElement('a');
      a.href = url; a.download = 'tikit-my-data.json'; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast('데이터를 내려받았어요.');
    } catch (err) { toast(err.message); }
  };
  $('#deleteData').onclick = () => {
    openModal('내 데이터 삭제', `
      <p class="modal-intro">계정과 연결된 공연 조회·찜·모의 예매 내역을 서버에서 삭제합니다. 삭제 후 복구할 수 없습니다.</p>
      <button class="primary" type="button" id="confirmDelete">내 데이터 삭제하기</button>
      <button class="secondary" type="button" id="cancelDelete">마이티킷으로 돌아가기</button>`);
    $('#cancelDelete').onclick = openOrders;
    const button = $('#confirmDelete');
    button.onclick = async () => {
      button.disabled = true;
      try {
        await authed('/users/me', { method: 'DELETE' });
        closeModal();
        tikitAuth.logout();
        onLogout();
        toast('계정과 연결된 데이터를 삭제했어요.');
      } catch (err) {
        button.disabled = false;
        toast(err.message);
      }
    };
  };
}

/* ---------- MBTI 취향 ---------- */
function openTaste() {
  if (!profile) { goLogin(); return; }
  const extrovert = profile.mbti.includes('E');
  const intro = extrovert ? '함께 열광하는 라이브의 에너지' : '마음에 오래 남는 나만의 감상';
  const picks = extrovert ? ['콘서트', '스포츠'] : ['전시', '클래식'];
  const copy = {
    '콘서트': '음악과 함성 속에서 만나는 새로운 에너지.',
    '스포츠': '함께 응원하고 짜릿한 순간을 나눠요.',
    '전시': '나만의 속도로 작품과 이야기를 만나보세요.',
    '클래식': '선율에 집중하며 깊은 여운을 느껴보세요.',
  };
  openModal('나를 닮은 취향의 발견', `
    <span class="tag">${escapeHTML(profile.mbti)} · ${escapeHTML(profile.name)}님의 취향 탐색</span><h3>${intro}</h3>
    <p class="modal-intro">새로운 공연 취향을 발견해 보세요. MBTI만으로 취향이 정해지지는 않아요. 다양한 장르를 자유롭게 탐색해 주세요.</p>
    <div class="taste-cards">${picks.map(c => `<div class="taste-card"><b>${c}</b><p>${copy[c]}</p><button class="text-link" type="button" data-taste-category="${c}">${c} 둘러보기 ↗</button></div>`).join('')}</div>
    <div class="demo-note">현재 추천은 MBTI의 E/I에 따른 탐색 예시입니다. 실제 사용자별 선호 통계가 아닙니다.</div>`);
  $$('[data-taste-category]').forEach(b => { b.onclick = () => { closeModal(); chooseCategory(b.dataset.tasteCategory); }; });
}

/* ---------- 이벤트 연결 ---------- */
function onLogout() {
  profile = null;
  favorites = [];
  renderAccount(null);
  renderCards();
}

document.addEventListener('click', e => {
  const mytikit = e.target.closest('[data-mytikit]');
  if (mytikit) { e.preventDefault(); openOrders(); return; }
  const cat = e.target.closest('[data-category]');
  if (cat) { e.preventDefault(); search = ''; $('#searchInput').value = ''; chooseCategory(cat.dataset.category); return; }
  const show = e.target.closest('[data-show]');
  if (show) { openBooking(show.dataset.show); return; }
  const fav = e.target.closest('[data-favorite]');
  if (fav) { toggleFavorite(fav.dataset.favorite); return; }
  const rank = e.target.closest('[data-rank]');
  if (rank) { renderRanking(rank.dataset.rank); $$('[data-rank]').forEach(b => b.classList.toggle('active', b === rank)); }
});

$('#searchForm').addEventListener('submit', e => {
  e.preventDefault();
  search = $('#searchInput').value.trim();
  expanded = true;
  syncUrl();
  loadList();
  $('#performances').scrollIntoView({ behavior: 'smooth' });
});
$('#searchInput').addEventListener('input', e => {
  if (!e.target.value && search) { search = ''; syncUrl(); loadList(); }
});
$('#sortSelect').addEventListener('change', loadList);
$('#moreButton').addEventListener('click', () => { expanded = !expanded; renderCards(); });
$('#seeAll').addEventListener('click', () => {
  category = '전체'; search = ''; $('#searchInput').value = ''; expanded = true; syncUrl(); loadList();
});
$('#prevSlide').onclick = () => slide(-1);
$('#nextSlide').onclick = () => slide(1);
$('#heroBook').onclick = () => openBooking(heroSlides[heroIndex].id);
$('#tasteButton').onclick = openTaste;
$('#mbtiBannerButton').onclick = openTaste;

$('#categoryChips').innerHTML = CATEGORIES.map(c => `<button type="button" data-category="${c}" class="chip">${c}</button>`).join('');
$('#quickCategories').innerHTML = CATEGORIES.slice(1).map(c =>
  `<button type="button" class="quick-category" data-category="${c}"><span class="category-icon"><svg viewBox="0 0 24 24" aria-hidden="true">${icons[c]}</svg></span>${c}</button>`).join('');

async function loadRanking() {
  try {
    ranking = await api('/performances/ranking?limit=50');
    renderRanking($('.rank-tabs .active')?.dataset.rank || 'all');
  } catch { /* 랭킹은 실패해도 화면은 계속 사용 */ }
}

/* ---------- 시작 ---------- */
(async () => {
  const params = new URLSearchParams(location.search);
  const qCategory = params.get('category');
  category = CATEGORIES.includes(qCategory) ? qCategory : '전체';
  search = (params.get('q') || '').trim().slice(0, 100);
  expanded = Boolean(search);
  $('#searchInput').value = search;
  const open = params.get('open');
  const resume = params.get('resume');

  renderGenreNav(category);
  renderAccount(null);

  try { profile = await tikitAuth.current(); } catch (err) { toast(err.message); }
  syncUrl(); // open/resume 같은 1회성 파라미터는 주소에서 지웁니다.

  try {
    const [shows, favs] = await Promise.all([
      api('/performances'),
      profile ? api('/favorites').catch(() => []) : Promise.resolve([]),
    ]);
    allShows = shows;
    favorites = favs;
  } catch (err) {
    toast(err.message);
  }
  slide(0);
  await loadList();
  loadRanking();

  try {
    const flash = sessionStorage.getItem('tikit.flash');
    if (flash) { sessionStorage.removeItem('tikit.flash'); toast(flash); }
  } catch { /* 무시 */ }

  if (open === 'mytikit') openOrders();
  if (resume === 'booking') {
    let saved = null;
    try { saved = JSON.parse(sessionStorage.getItem(PENDING_BOOKING_KEY)); sessionStorage.removeItem(PENDING_BOOKING_KEY); } catch { /* 무시 */ }
    if (saved?.showId) {
      try {
        await loadBooking(saved.showId, saved);
        if (profile) renderPayment(); else renderBooking();
      } catch (err) { toast(err.message); }
    }
  }
})();
