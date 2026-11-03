'use strict';
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const won = n => n.toLocaleString('ko-KR') + '원';
const escapeHTML = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const photo = (id, width = 600) => `https://images.unsplash.com/${id}?auto=format&fit=crop&w=${width}&q=80`;
const categories = ['전체','콘서트','뮤지컬','스포츠','전시','클래식','연극'];
const icons = {
  '콘서트':'<path d="M9 18V5l12-2v13M9 9l12-2"/><ellipse cx="6" cy="18" rx="3" ry="2.5"/><ellipse cx="18" cy="16" rx="3" ry="2.5"/>',
  '뮤지컬':'<path d="M3 4c4 2 8 2 12 0v8c0 5-6 8-6 8s-6-3-6-8Z"/><path d="m6 10 2 1m3 0 2-1M7 15q2 2 4 0M18 6l3-1v8c0 4-4 7-4 7"/>',
  '스포츠':'<circle cx="12" cy="12" r="9"/><path d="m9 9 6-1 2 5-5 4-5-4ZM12 3 9 9M21 11l-4 2M15 20l-3-3M4 16l3-3M4 7l5 2"/>',
  '전시':'<rect x="3" y="4" width="18" height="16" rx="1"/><path d="m4 17 6-6 4 4 3-3 4 4"/><circle cx="16" cy="8" r="1.5"/>',
  '클래식':'<path d="M8 5c4 3 8 1 12 3v12H3v-8c0-4 5-3 5-7ZM3 15h17M7 15v5m4-5v5m4-5v5M8 5V2"/>',
  '연극':'<path d="M4 4h16v16H4ZM4 5l8 7 8-7M4 17l5-7m11 7-5-7M12 12v8"/>'
};
const shows = [
 {id:'city',category:'콘서트',title:'2026 시티 라이츠 페스티벌',english:'CITY\nLIGHTS',sub:'MUSIC FESTIVAL',image:'photo-1470229722913-7c0e2dbbafd3',style:'city',venue:'올림픽공원 88잔디마당',date:'2026.11.21 - 11.22',start:'2026-11-21',price:99000,badge:'단독 판매',tag:'티킷 PICK',days:2,slots:['14:00','18:00']},
 {id:'opera',category:'뮤지컬',title:'뮤지컬 〈오페라의 유령〉',english:'The\nPhantom\nof the Opera',sub:'THE MUSICAL',image:'photo-1503095396549-807759245b35',style:'opera',venue:'샤롯데씨어터',date:'2026.11.10 - 2027.01.31',start:'2026-11-10',price:80000,badge:'화제의 뮤지컬',tag:'인기 급상승',days:7,slots:['14:00','19:30']},
 {id:'color',category:'전시',title:'컬러 오브 모먼트 : 일상의 조각들',english:'COLOR\nOF\nMOMENT',sub:'COLLECT YOUR MOMENTS',image:'photo-1579783902614-a3fb3927b6a5',style:'art',venue:'그라운드시소 성수',date:'2026.11.05 - 2027.02.28',start:'2026-11-05',price:18000,badge:'새로운 시선',tag:'추천 전시',days:7,slots:['10:00','12:00','14:00','16:00']},
 {id:'jazz',category:'콘서트',title:'블루 아워 재즈 나이트',english:'Blue Hour\nJazz Night',sub:'A NIGHT TO REMEMBER',image:'photo-1511192336575-5a79af67a629',style:'jazz',venue:'노들섬 라이브하우스',date:'2026.11.14 - 11.15',start:'2026-11-14',price:65000,badge:'가을밤의 재즈',tag:'매진 임박',days:2,slots:['18:00','20:00']},
 {id:'baseball',category:'스포츠',title:'서울 베이스볼 올스타 매치',english:'PLAY\nYOUR\nGAME.',sub:'2026 BASEBALL ALL STARS',image:'photo-1471295253337-3ceaaedca402',style:'sport',venue:'잠실야구장',date:'2026.11.07 - 11.08',start:'2026-11-07',price:25000,badge:'스페셜 매치',tag:'주말 추천',days:2,slots:['14:00','18:00']},
 {id:'classic',category:'클래식',title:'가을을 닮은 선율 : 피아노 리사이틀',english:'Autumn\nSonata',sub:'PIANO RECITAL',image:'photo-1520523839897-bd0b52f945a0',style:'classic',venue:'예술의전당 콘서트홀',date:'2026.11.18 - 11.20',start:'2026-11-18',price:50000,badge:'깊어지는 선율',tag:'티킷 PICK',days:3,slots:['19:30']},
 {id:'theater',category:'연극',title:'연극 〈우리가 빛나던 계절〉',english:'우리가\n빛나던\n계절',sub:'OUR SHINING DAYS',image:'photo-1507676184212-d03ab07a01bf',style:'theater',venue:'대학로 아트원씨어터',date:'2026.11.06 - 12.27',start:'2026-11-06',price:35000,badge:'마음을 잇는 이야기',tag:'대학로 추천',days:7,slots:['15:00','19:00']},
 {id:'dance',category:'뮤지컬',title:'뮤지컬 〈미드나잇 인 서울〉',english:'MIDNIGHT\nIN SEOUL',sub:'THE CITY IS YOUR STAGE',image:'photo-1516280440614-37939bbacd81',style:'dance',venue:'블루스퀘어 신한카드홀',date:'2026.11.13 - 12.20',start:'2026-11-13',price:70000,badge:'새로운 무대',tag:'신규 오픈',days:7,slots:['14:30','19:30']}
];
function read(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } }
let storageAvailable = true;
function save(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { storageAvailable = false; toast('브라우저 저장 공간을 사용할 수 없어 현재 화면에서만 유지됩니다.'); } }
const legacyProfile = read('tikit.profile', null);
let profile = demoAuth.current();
let orders = read('tikit.orders', []); if (!Array.isArray(orders)) orders = [];
let favorites = read('tikit.favorites', []); if (!Array.isArray(favorites)) favorites = [];
let events = read('tikit.events', []); if (!Array.isArray(events)) events = [];
let category = '전체', search = '', expanded = false, heroIndex = 0, booking = null;
const modal = $('#modal'); let returnFocus;
function toast(message) { $('#toast').textContent = message; $('#toast').classList.add('show'); clearTimeout(toast.timer); toast.timer = setTimeout(() => $('#toast').classList.remove('show'), 3200); }
function openModal(title, content) { returnFocus = document.activeElement; $('#modalContent').innerHTML = `<div class="modal-header"><h2>${title}</h2><button class="close-modal" aria-label="창 닫기" data-close>×</button></div><div class="modal-body">${content}</div>`; if (!modal.open) modal.showModal(); modal.scrollTop = 0; }
function closeModal() { modal.close(); returnFocus?.focus(); }
modal.addEventListener('click', e => { if (e.target.closest('[data-close]')) closeModal(); if (e.target === modal) { const r = modal.getBoundingClientRect(); if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) closeModal(); } });
function track(type, show) { if (!profile?.consent) return; events.push({id:crypto.randomUUID(),userId:profile.id,mbti:profile.mbti,type,performanceId:show.id,category:show.category,createdAt:new Date().toISOString()}); events = events.slice(-500); save('tikit.events', events); }
function poster(s) { return `<div class="poster poster-${s.style}"><img src="${photo(s.image)}" alt="" loading="lazy"><span class="poster-label">${s.badge}</span><span class="poster-eyebrow">TIKIT PRESENTS · 2026</span><span class="poster-title">${s.english}</span><span class="poster-sub">${s.sub}</span><span class="poster-date">${s.date} · SEOUL</span></div>`; }
function renderCards() {
  let filtered = shows.filter(s => (category === '전체' || s.category === category) && `${s.title} ${s.venue} ${s.category}`.toLowerCase().includes(search.toLowerCase()));
  if ($('#sortSelect').value === 'date') filtered.sort((a,b)=>a.start.localeCompare(b.start));
  if ($('#sortSelect').value === 'price') filtered.sort((a,b)=>a.price-b.price);
  const visible = expanded ? filtered : filtered.slice(0,4);
  $('#performanceGrid').innerHTML = visible.map(s => `<article class="show-card"><button class="poster-button" data-show="${s.id}" aria-label="${s.title} 상세 및 예매">${poster(s)}</button><button class="favorite ${favorites.includes(s.id)?'saved':''}" data-favorite="${s.id}" aria-label="${s.title} 찜하기" aria-pressed="${favorites.includes(s.id)}">${favorites.includes(s.id)?'♥':'♡'}</button><div class="show-info"><div class="tags"><span class="tag">${s.tag}</span><span class="tag neutral">${s.category}</span></div><button class="show-title" data-show="${s.id}">${s.title}</button><p>${s.venue}</p><p>${s.date}</p><div class="price-line">${won(s.price)} <small>부터</small></div></div></article>`).join('');
  $('#emptyState').hidden = filtered.length > 0;
  $('#moreButton').hidden = filtered.length <= 4;
  $('#moreButton').innerHTML = expanded ? '간략히 보기 <span>−</span>' : '더 많은 설렘 만나보기 <span>＋</span>';
  $('#listTitle').innerHTML = search ? `“${escapeHTML(search)}” 검색 결과 <span>✦</span>` : category === '전체' ? '지금, 가장 설레는 공연 <span>✦</span>' : `${category}, 나의 다음 설렘 <span>✦</span>`;
  $$('[data-category]').forEach(b => { b.classList.toggle('active', b.dataset.category === category); b.setAttribute('aria-pressed', String(b.dataset.category === category)); });
}
function chooseCategory(c) { category = c; expanded = false; renderCards(); $('#performances').scrollIntoView({behavior:'smooth',block:'start'}); }
$('#genreNav').innerHTML = categories.map(c=>`<button data-category="${c}" class="${c==='전체'?'active':''}">${c==='전체'?'홈':c}</button>`).join('');
$('#categoryChips').innerHTML = categories.map(c=>`<button data-category="${c}" class="chip ${c==='전체'?'active':''}">${c}</button>`).join('');
$('#quickCategories').innerHTML = categories.slice(1).map(c=>`<button class="quick-category" data-category="${c}"><span class="category-icon"><svg viewBox="0 0 24 24" aria-hidden="true">${icons[c]}</svg></span>${c}</button>`).join('');
document.addEventListener('click', e=>{
  const cat = e.target.closest('[data-category]'); if(cat) chooseCategory(cat.dataset.category);
  const show = e.target.closest('[data-show]'); if(show) openBooking(show.dataset.show);
  const favorite = e.target.closest('[data-favorite]'); if(favorite) { const id = favorite.dataset.favorite; favorites = favorites.includes(id) ? favorites.filter(x=>x!==id) : [...favorites,id]; save('tikit.favorites',favorites); renderCards(); toast(favorites.includes(id)?'좋아하는 공연에 담았어요. 마이티킷에서 확인하세요.':'찜한 공연에서 해제했어요.'); }
  const rank = e.target.closest('[data-rank]'); if(rank) { renderRanking(rank.dataset.rank); $$('[data-rank]').forEach(b=>b.classList.toggle('active',b===rank)); }
  const info = e.target.closest('[data-info]'); if(info) showInfo(info.dataset.info);
});
$('#searchForm').addEventListener('submit',e=>{e.preventDefault(); search=$('#searchInput').value.trim(); expanded=true; renderCards(); $('#performances').scrollIntoView({behavior:'smooth'});});
$('#searchInput').addEventListener('input',e=>{if(!e.target.value){search='';renderCards();}});
$('#sortSelect').addEventListener('change',renderCards);
$('#moreButton').addEventListener('click',()=>{expanded=!expanded;renderCards();});
$('#seeAll').addEventListener('click',()=>{category='전체';search='';$('#searchInput').value='';expanded=true;renderCards();});
function renderRanking(c='all') { $('#rankingGrid').innerHTML=shows.filter(s=>c==='all'||s.category===c).slice(0,3).map((s,i)=>`<button class="rank-card" data-show="${s.id}"><span class="rank-number">${i+1}</span><img src="${photo(s.image,200)}" alt="" loading="lazy"><div class="rank-copy"><small>${s.category}</small><b>${s.title}</b><p>${s.venue}</p></div></button>`).join(''); }
const heroShows=['city','opera','color'];
function slide(delta) { heroIndex=(heroIndex+delta+3)%3; const s=shows.find(x=>x.id===heroShows[heroIndex]); const titles=['우리의 밤은<br>지금부터 <em>시작이야.</em>','오래 기다려온<br>그 무대, <em>그 전율.</em>','일상에 새로운<br>색을 <em>더해볼까요.</em>']; $('#heroTitle').innerHTML=titles[heroIndex]; $('#heroDescription').innerHTML=`${s.title}<br>${s.venue} · ${s.date}`; $('#heroImage').src=photo(s.image,1400); $('#heroImage').alt=s.title+' 공연 분위기 이미지'; $('#heroIndex').textContent=String(heroIndex+1).padStart(2,'0'); $('#slideProgress').style.width=`${(heroIndex+1)/3*100}%`; $('.hero-sticker').innerHTML=heroIndex===0?'FEEL<br>YOUR<br><span>VIBE</span><small>SEOUL · 2026</small>':heroIndex===1?'THE<br>STAGE<br><span>IS YOURS</span><small>MUSICAL · 2026</small>':'COLOR<br>YOUR<br><span>DAYS</span><small>EXHIBITION · 2026</small>'; $('#heroBook').innerHTML=`${heroIndex===0?'페스티벌':heroIndex===1?'뮤지컬':'전시'} 만나보기 <span>↗</span>`; }
$('#prevSlide').onclick=()=>slide(-1); $('#nextSlide').onclick=()=>slide(1); $('#heroBook').onclick=()=>openBooking(heroShows[heroIndex]);
const mbtis=['INTJ','INTP','ENTJ','ENTP','INFJ','INFP','ENFJ','ENFP','ISTJ','ISFJ','ESTJ','ESFJ','ISTP','ISFP','ESTP','ESFP'];
function updateAccount(){ $('#loginButton').textContent=profile?`${profile.name}님`:'로그인'; $('#signupButton').textContent=profile?'로그아웃':'회원가입'; }
function openSignup(after) {
  openModal('나의 취향, 티킷에서 시작하기',`<p class="modal-intro">설레는 순간을 함께 찾아요.<br>MBTI는 공연 취향을 이해하는 데 사용됩니다.</p><form id="signupForm"><label class="form-field">닉네임 <span class="required">*</span><input name="nickname" required maxlength="20" autocomplete="nickname" placeholder="티킷에서 사용할 이름"></label><label class="form-field">이메일 <span class="required">*</span><input name="email" type="email" required maxlength="100" autocomplete="email" placeholder="hello@example.com"></label><p class="field-title">나의 MBTI <span class="required">* 필수</span></p><div class="mbti-options">${mbtis.map(m=>`<label class="mbti-option"><input type="radio" name="mbti" value="${m}" required><span>${m}</span></label>`).join('')}</div><label class="check-label"><input type="checkbox" name="consent" required><span>[필수] MBTI·공연 조회·모의 예매 내역을 공연 취향 분석 목적으로 수집하는 데 동의합니다. 데이터는 이 브라우저에 보관되며, 마이티킷에서 삭제할 수 있습니다.</span></label><div class="demo-note">시연용 가입입니다. 비밀번호와 실제 결제 정보는 수집하지 않으며, 다른 기기와 계정이 연동되지 않습니다.</div><button class="primary" type="submit">동의하고 시작하기</button></form>`);
  const form = $('#signupForm');
  $('[name=email]', form).closest('label').insertAdjacentHTML('afterend', `<label class="form-field">비밀번호 <span class="required">*</span><span class="password-control"><input name="password" type="password" required minlength="8" maxlength="128" autocomplete="new-password" placeholder="8~128자 입력"><button type="button" data-toggle-password="password" aria-label="비밀번호 표시" aria-pressed="false">보기</button></span></label><label class="form-field">비밀번호 확인 <span class="required">*</span><span class="password-control"><input name="passwordConfirm" type="password" required minlength="8" maxlength="128" autocomplete="new-password" placeholder="비밀번호를 다시 입력해 주세요"><button type="button" data-toggle-password="passwordConfirm" aria-label="비밀번호 확인 표시" aria-pressed="false">보기</button></span></label>`);
  $('.demo-note', form).textContent = '이 브라우저에서만 이용하는 시연용 계정입니다. 비밀번호는 원문 대신 검증값으로 저장하며, 다른 기기와 연동되지 않습니다. 실제 사용하는 비밀번호는 입력하지 마세요.';
  form.insertAdjacentHTML('beforeend', '<p class="form-error" role="alert" hidden></p><button class="secondary" type="button" id="signupToLogin">이미 계정이 있나요? 로그인</button>');
  $('#signupToLogin').onclick = () => openLogin(after);
  const password = $('[name=password]', form), confirm = $('[name=passwordConfirm]', form);
  const validate = () => confirm.setCustomValidity(password.value === confirm.value ? '' : '비밀번호가 일치하지 않습니다.');
  password.oninput = validate; confirm.oninput = validate;
  attachPasswordToggles(form);
  form.onsubmit = async e => {
    e.preventDefault(); if (form.dataset.busy) return;
    const f = new FormData(form), name = f.get('nickname').trim(), email = f.get('email').trim().toLowerCase();
    if (!name) { showAuthError(form, '닉네임을 입력해 주세요.'); return; }
    validate(); if (!form.reportValidity()) return;
    form.dataset.busy = 'true'; const button = $('[type=submit]', form); button.disabled = true; button.textContent = '가입 중…';
    try {
      const legacyId = legacyProfile?.email?.toLowerCase() === email ? legacyProfile.id : null;
      const account = await demoAuth.signup({id:legacyId || crypto.randomUUID(),name,email,mbti:f.get('mbti'),consent:true,consentedAt:new Date().toISOString()}, f.get('password'));
      profile = account; try { localStorage.removeItem('tikit.profile'); } catch {}
      updateAccount(); if (form.isConnected) { closeModal(); if(after) after(); } toast(`${name}님, 가입이 완료됐어요!`);
    } catch(error) { showAuthError(form, error.message); }
    finally { delete form.dataset.busy; button.disabled = false; button.textContent = '동의하고 시작하기'; }
  };
}
function showAuthError(form, message) { const error = $('.form-error', form); error.textContent = message; error.hidden = false; }
function attachPasswordToggles(form) { $$('[data-toggle-password]', form).forEach(button => button.onclick = () => { const input = $(`[name="${button.dataset.togglePassword}"]`, form); const visible = input.type === 'password'; input.type = visible ? 'text' : 'password'; button.textContent = visible ? '숨기기' : '보기'; button.setAttribute('aria-pressed', String(visible)); button.setAttribute('aria-label', `${input.name === 'passwordConfirm' ? '비밀번호 확인' : '비밀번호'} ${visible ? '숨기기' : '표시'}`); }); }
function openLogin(after) {
  openModal('다시 만나서 반가워요', `<p class="modal-intro">가입한 이메일과 비밀번호로 로그인해 주세요.<br>이 브라우저에 가입한 계정으로만 이용할 수 있습니다.</p><form id="loginForm"><label class="form-field">이메일<input name="email" type="email" required maxlength="100" autocomplete="username" placeholder="hello@example.com"></label><label class="form-field">비밀번호<span class="password-control"><input name="password" type="password" required maxlength="128" autocomplete="current-password" placeholder="비밀번호 입력"><button type="button" data-toggle-password="password" aria-label="비밀번호 표시" aria-pressed="false">보기</button></span></label><p class="form-error" role="alert" hidden></p><button class="primary" type="submit">로그인</button><button class="secondary" type="button" id="loginToSignup">처음이신가요? 회원가입</button></form><div class="demo-note">이전 시연에서 비밀번호 없이 가입했다면 같은 이메일로 다시 가입해 비밀번호를 설정해 주세요. 기존 예매 내역을 이어서 볼 수 있습니다.</div>`);
  const form = $('#loginForm'); attachPasswordToggles(form); $('#loginToSignup').onclick = () => openSignup(after);
  form.onsubmit = async e => { e.preventDefault(); if(form.dataset.busy) return; form.dataset.busy = 'true'; const button = $('[type=submit]', form); button.disabled = true; button.textContent = '로그인 중…';
    try { const f = new FormData(form); const account = await demoAuth.login(f.get('email'), f.get('password')); profile = account; updateAccount(); if(form.isConnected) { closeModal(); if(after) after(); } toast(`${profile.name}님, 반가워요!`); }
    catch(error) { showAuthError(form, error.message); }
    finally { delete form.dataset.busy; button.disabled = false; button.textContent = '로그인'; }
  };
}
$('#signupButton').onclick=()=>{if(profile){try{demoAuth.logout();}catch{}profile=null;updateAccount();toast('로그아웃했어요.');}else openSignup();};
$('#loginButton').onclick=()=>profile ? openTaste() : openLogin();
function availableDates(s){return Array.from({length:s.days},(_,i)=>{const d=new Date(`${s.start}T12:00:00`);d.setDate(d.getDate()+i);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;});}
function detailTop(s){return `<div class="detail-top">${poster(s)}<div><span class="tag">${s.category}</span><h3>${s.title}</h3><p>${s.venue}</p><p>${s.date}</p><p>시연 공연 · 만 7세 이상 · 약 120분</p></div></div>`;}
function total(){const s=shows.find(s=>s.id===booking.showId);return (s.price+booking.premium)*booking.quantity;}
function openBooking(id){const s=shows.find(s=>s.id===id); track('performance_view',s);booking={showId:id,date:availableDates(s)[0],slot:s.slots[0],premium:0,quantity:1,paymentMethod:'간편결제'};renderBooking();}
function renderBooking(){const s=shows.find(s=>s.id===booking.showId);openModal('설렘을 예약하는 시간',`<div class="booking-steps"><span class="current">01 날짜 · 회차</span><span>──</span><span>02 모의 결제</span><span>──</span><span>03 완료</span></div>${detailTop(s)}<p class="field-title">관람 날짜 선택</p><div class="date-options">${availableDates(s).map(date=>{const d=new Date(date+'T12:00:00');return `<button class="date-option ${booking.date===date?'selected':''}" data-date="${date}" aria-pressed="${booking.date===date}"><small>${['일','월','화','수','목','금','토'][d.getDay()]}</small>${d.getMonth()+1}.${String(d.getDate()).padStart(2,'0')}</button>`;}).join('')}</div><p class="field-title">회차 선택</p><div class="slot-options">${s.slots.map(slot=>`<button class="slot-option ${booking.slot===slot?'selected':''}" data-slot="${slot}" aria-pressed="${booking.slot===slot}">${slot}</button>`).join('')}</div><div class="seat-quantity"><label><p class="field-title">좌석 등급</p><select id="seatSelect"><option value="0">일반석 · ${won(s.price)}</option><option value="30000">프리미엄석 · ${won(s.price+30000)}</option></select></label><label><p class="field-title">예매 수량</p><select id="quantitySelect">${[1,2,3,4].map(n=>`<option value="${n}">${n}매</option>`).join('')}</select></label></div><div class="summary-box"><div class="summary-line"><span>티켓 금액</span><span id="ticketSubtotal">${won(total())}</span></div><div class="summary-line"><span>예매 수수료</span><span>0원</span></div><div class="summary-line total"><span>총 결제 금액</span><b id="bookingTotal">${won(total())}</b></div></div><button class="primary" id="goPayment">${profile?'모의 결제로 이동':'회원가입 후 모의 결제로 이동'} →</button>`);
  $('#seatSelect').value=booking.premium; $('#quantitySelect').value=booking.quantity;
  $$('[data-date]').forEach(b=>b.onclick=()=>{booking.date=b.dataset.date; $$('[data-date]').forEach(x=>{x.classList.toggle('selected',x===b);x.setAttribute('aria-pressed',String(x===b));});});
  $$('[data-slot]').forEach(b=>b.onclick=()=>{booking.slot=b.dataset.slot;$$('[data-slot]').forEach(x=>{x.classList.toggle('selected',x===b);x.setAttribute('aria-pressed',String(x===b));});});
  const update=()=>{$('#ticketSubtotal').textContent=won(total());$('#bookingTotal').textContent=won(total());};
  $('#seatSelect').onchange=e=>{booking.premium=Number(e.target.value);update();};$('#quantitySelect').onchange=e=>{booking.quantity=Number(e.target.value);update();};
  $('#goPayment').textContent = profile ? '모의 결제로 이동 →' : '로그인 후 모의 결제로 이동 →';
  $('#goPayment').onclick=()=>{if(!profile)openLogin(renderPayment);else renderPayment();};
}
function renderPayment(){const s=shows.find(s=>s.id===booking.showId);openModal('모의 결제',`<div class="booking-steps"><span>01 날짜 · 회차</span><span>──</span><span class="current">02 모의 결제</span><span>──</span><span>03 완료</span></div>${detailTop(s)}<div class="summary-box"><div class="summary-line"><span>예매자 / MBTI</span><span>${escapeHTML(profile.name)} / ${escapeHTML(profile.mbti)}</span></div><div class="summary-line"><span>관람 일시</span><span>${booking.date} ${booking.slot}</span></div><div class="summary-line"><span>좌석 / 수량</span><span>${booking.premium?'프리미엄석':'일반석'} / ${booking.quantity}매</span></div><div class="summary-line total"><span>총 결제 금액</span><b>${won(total())}</b></div></div><p class="field-title">결제 방법</p><div class="payment-options">${['간편결제','신용카드','계좌이체'].map(m=>`<button class="payment-option ${booking.paymentMethod===m?'selected':''}" data-payment="${m}" aria-pressed="${booking.paymentMethod===m}">${m}</button>`).join('')}</div><div class="demo-note">실제 결제가 발생하지 않는 모의 결제입니다.<br>카드번호·계좌번호를 입력하지 마세요. 완료 시 예매 내역만 이 브라우저에 저장됩니다.</div><form id="paymentForm"><label class="check-label"><input type="checkbox" required><span>공연·날짜·회차·금액을 확인했으며 모의 예매에 동의합니다.</span></label><button class="primary" type="submit">${won(total())} 모의 결제하기</button></form><button class="secondary" id="backToDates">← 날짜·회차 다시 선택</button>`);
  $$('[data-payment]').forEach(b=>b.onclick=()=>{booking.paymentMethod=b.dataset.payment;$$('[data-payment]').forEach(x=>{x.classList.toggle('selected',x===b);x.setAttribute('aria-pressed',String(x===b));});});
  $('#backToDates').onclick=renderBooking;
  $('#paymentForm').onsubmit=e=>{e.preventDefault();$('#paymentForm button').disabled=true;const order={id:crypto.randomUUID(),userId:profile.id,mbti:profile.mbti,performanceId:s.id,performanceTitle:s.title,category:s.category,venue:s.venue,performanceDate:booking.date,sessionTime:booking.slot,seatGrade:booking.premium?'PREMIUM':'STANDARD',quantity:booking.quantity,unitPrice:s.price+booking.premium,amount:total(),currency:'KRW',paymentMethod:booking.paymentMethod,status:'MOCK_PAID',isMock:true,createdAt:new Date().toISOString()};orders.unshift(order);save('tikit.orders',orders);track('mock_purchase',s);openModal('모의 예매 완료',`<div class="success"><div class="success-icon">✓</div><h3>새로운 설렘이 기다리고 있어요!</h3><p>${s.title}<br>${order.performanceDate} ${order.sessionTime} · ${order.quantity}매<br>모의 결제 금액 ${won(order.amount)}</p><span class="tag">실제 청구 금액 0원</span><p>${storageAvailable?'예매 내역이 이 브라우저에 저장되었습니다.':'저장 공간을 사용할 수 없어 새로고침 시 내역이 사라집니다.'}</p></div><button class="primary" id="viewOrders">예매 내역 확인하기</button><button class="secondary" data-close>다른 공연 둘러보기</button>`);$('#viewOrders').onclick=openOrders;};
}
function openOrders(){const mine=profile?orders.filter(o=>o.userId===profile.id):[];const liked=shows.filter(s=>favorites.includes(s.id));openModal('마이티킷',`<p class="modal-intro">${profile?`${escapeHTML(profile.name)}님의 설레는 순간들 <span class="tag">${escapeHTML(profile.mbti)}</span>`:'회원가입 후 모의 예매를 시작해 보세요.'}</p><p class="field-title">나의 예매 내역 · ${mine.length}건</p>${mine.length?mine.map(o=>`<article class="order-card"><span class="order-status">모의 예매 완료 · 실제 결제 없음</span><h3>${escapeHTML(o.performanceTitle)}</h3><p>${escapeHTML(o.performanceDate)} ${escapeHTML(o.sessionTime)} · ${escapeHTML(o.venue)}<br>${o.seatGrade==='PREMIUM'?'프리미엄석':'일반석'} ${o.quantity}매 · ${won(o.amount)}</p><footer><span>예매번호 ${escapeHTML(o.id.slice(0,8).toUpperCase())}</span><span>${new Date(o.createdAt).toLocaleDateString('ko-KR')}</span></footer></article>`).join(''):'<div class="demo-note">아직 예매한 공연이 없어요. 마음에 드는 공연을 골라 보세요.</div>'}<p class="field-title">찜한 공연 · ${liked.length}개</p>${liked.map(s=>`<button class="secondary" data-show="${s.id}">${s.title} ↗</button>`).join('')}${profile?'<button class="primary" id="exportData">내 취향·예매 데이터 내려받기 (JSON)</button><button class="secondary" id="deleteData">내 프로필·취향·예매 데이터 삭제</button>':'<button class="primary" id="ordersSignup">회원가입하고 시작하기</button>'}`);
  if($('#ordersSignup'))$('#ordersSignup').onclick=()=>openSignup(openOrders);
  if($('#exportData'))$('#exportData').onclick=()=>{const payload={schemaVersion:1,exportedAt:new Date().toISOString(),profile,orders:mine,events:events.filter(x=>x.userId===profile.id)};const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='tikit-my-data.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('데이터를 내려받았어요.');};
  if($('#deleteData'))$('#deleteData').onclick=()=>{openModal('내 데이터 삭제',`<p class="modal-intro">현재 프로필과 연결된 공연 조회·모의 예매 내역을 이 브라우저에서 삭제합니다. 삭제 후 복구할 수 없습니다.</p><button class="primary" id="confirmDelete">내 데이터 삭제하기</button><button class="secondary" id="cancelDelete">마이티킷으로 돌아가기</button>`);$('#cancelDelete').onclick=openOrders;$('#confirmDelete').onclick=()=>{try{demoAuth.remove(profile.id);}catch{toast('계정을 삭제할 수 없습니다. 다시 시도해 주세요.');return;}orders=orders.filter(o=>o.userId!==profile.id);events=events.filter(o=>o.userId!==profile.id);save('tikit.orders',orders);save('tikit.events',events);profile=null;try{localStorage.removeItem('tikit.profile');}catch{}updateAccount();closeModal();toast('현재 프로필과 연결된 데이터를 삭제했어요.');};};
}
$('#ordersButton').onclick=openOrders;
function openTaste(){if(!profile){openSignup(openTaste);return;}const intro=profile.mbti.includes('E')?'함께 열광하는 라이브의 에너지':'마음에 오래 남는 나만의 감상';const picks=profile.mbti.includes('E')?['콘서트','스포츠']:['전시','클래식'];openModal('나를 닮은 취향의 발견',`<span class="tag">${escapeHTML(profile.mbti)} · ${escapeHTML(profile.name)}님의 취향 탐색</span><h3>${intro}</h3><p class="modal-intro">새로운 공연 취향을 발견해 보세요. MBTI만으로 취향이 정해지지는 않아요. 다양한 장르를 자유롭게 탐색해 주세요.</p><div class="taste-cards">${picks.map(c=>`<div class="taste-card"><b>${c}</b><p>${c==='콘서트'?'음악과 함성 속에서 만나는 새로운 에너지.':c==='스포츠'?'함께 응원하고 짜릿한 순간을 나눠요.':c==='전시'?'나만의 속도로 작품과 이야기를 만나보세요.':'선율에 집중하며 깊은 여운을 느껴보세요.'}</p><button class="text-link" data-taste-category="${c}">${c} 둘러보기 ↗</button></div>`).join('')}</div><div class="demo-note">현재 추천은 MBTI의 E/I에 따른 탐색 예시입니다. 실제 사용자별 선호 통계가 아닙니다. 수집한 공연 조회와 모의 예매 기록은 향후 취향 분석에 활용할 수 있습니다.</div>`);$$('[data-taste-category]').forEach(b=>b.onclick=()=>{closeModal();chooseCategory(b.dataset.tasteCategory);});}
$('#tasteButton').onclick=openTaste;$('#mbtiBannerButton').onclick=openTaste;
function showInfo(type){const info={about:['티킷 소개','취향이 만나는 순간, TIKIT. 콘서트·뮤지컬·스포츠·전시·클래식·연극을 탐색하고 나의 다음 설렘을 찾아보세요. 모든 공연 정보와 예매는 프론트엔드 시연용입니다.'],terms:['시연 서비스 이용 안내','실제 티켓이 발급되거나 결제가 이루어지지 않습니다. 공연명·공연장·일정·가격은 예시이며 실제 판매 정보와 다를 수 있습니다.'],privacy:['개인정보 처리 안내','닉네임, 이메일, MBTI, 동의 시각, 공연 조회 및 모의 예매 내역과 솔트를 포함한 비밀번호 검증값을 이 브라우저의 localStorage에 저장합니다. 로그인 상태는 현재 탭의 sessionStorage에 유지합니다. 서버나 DB로 전송하지 않습니다. 마이티킷에서 JSON으로 내려받거나 현재 프로필의 데이터를 삭제할 수 있습니다. 공용 기기에서는 이용 후 데이터를 삭제해 주세요.'],help:['고객센터','현재 프론트엔드 시연 버전입니다. 공연 선택 → 날짜·회차 선택 → MBTI 필수 가입 → 모의 결제 → 마이티킷 순서로 체험할 수 있습니다. 실제 고객센터와 결제 서비스는 연결되어 있지 않습니다.']};openModal(info[type][0],`<p class="modal-intro">${info[type][1]}</p><button class="primary" data-close>확인</button>`);}
renderCards();renderRanking();updateAccount();
