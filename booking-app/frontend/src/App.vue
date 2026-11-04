<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from './api'
import { availableDates } from './utils'
import HomePage from './components/HomePage.vue'
import TicketsPage from './components/TicketsPage.vue'
import ModalDialog from './components/ModalDialog.vue'
import AuthForm from './components/AuthForm.vue'
import BookingPanel from './components/BookingPanel.vue'

const categories = ['전체','콘서트','뮤지컬','스포츠','전시','클래식','연극']
const shows = ref([])
const profile = ref(null)
const loading = ref(true)
const loadError = ref('')
const favorites = ref([])
try { const saved = JSON.parse(localStorage.getItem('tikit.db.favorites')); if (Array.isArray(saved)) favorites.value = saved } catch { /* Empty favorites when storage is unavailable. */ }
const category = ref('전체')
const searchInput = ref('')
const search = ref('')
const expanded = ref(false)
const isTickets = ref(location.hash === '#my-tickets')
const modal = ref('')
const modalTitle = ref('')
const booking = ref(null)
const bookingConfirmation = ref(false)
const selectedShow = computed(() => shows.value.find(show => show.id === booking.value?.showId))
const cancelOrder = ref(null)
const busy = ref(false)
const revision = ref(0)
const toastMessage = ref('')
let toastTimer
let authAfter = null
const info = {
  about: ['티킷 소개', '취향이 만나는 순간, TIKIT. 공연을 탐색하고 예매와 결제 상태를 확인하세요. 나의 다음 설렘을 찾아보세요.'],
  terms: ['이용 안내', '실제 결제·환불·티켓 발급은 발생하지 않습니다. 예매·결제 내역을 확인하고 관리할 수 있습니다.'],
  privacy: ['개인정보 처리 안내', '이름, 이메일, 비밀번호 해시, MBTI와 동의 시각을 서버 DB에 저장합니다. 공연 조회, 예매 시작·요청·결제 완료·취소 시각과 상태 이력은 수요·전환율·취소 패턴 분석을 위해 보관합니다. 로그인에는 HttpOnly 세션 쿠키를 사용하며 찜 목록은 현재 브라우저에 저장합니다.'],
  help: ['이용 방법', '공연 선택 → 날짜·회차·좌석·수량 선택 → 로그인 → 예매하기 → 결제하기. 마이티킷에서 예매·결제 내역을 확인하거나 예매를 취소할 수 있습니다.'],
}
const infoKey = ref('about')
const tasteCategories = computed(() => profile.value?.mbti.includes('E') ? ['콘서트','스포츠'] : ['전시','클래식'])
const tasteText = { 콘서트: '음악과 함성 속에서 만나는 새로운 에너지.', 스포츠: '함께 응원하고 짜릿한 순간을 나눠요.', 전시: '나만의 속도로 작품과 이야기를 만나보세요.', 클래식: '선율에 집중하며 깊은 여운을 느껴보세요.' }
function toast(message) {
  toastMessage.value = message
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => toastMessage.value = '', 3200)
}
async function initialize() {
  loading.value = true
  loadError.value = ''
  try {
    const [performances, account] = await Promise.all([api('/performances'), api('/me')])
    shows.value = performances
    profile.value = account
  } catch (e) { loadError.value = e.message }
  finally { loading.value = false }
}
function closeModal() { modal.value = ''; authAfter = null }
function openModal(kind, title) { modal.value = kind; modalTitle.value = title }
function openAuth(mode, after = null) {
  authAfter = after
  openModal(mode, mode === 'signup' ? '나의 취향, 티킷에서 시작하기' : '다시 만나서 반가워요')
}
function authenticated(account) {
  const after = authAfter
  profile.value = account
  closeModal()
  toast(`${account.name}님, 반가워요!`)
  after?.()
}
async function signupOrLogout() {
  if (!profile.value) { openAuth('signup'); return }
  if (busy.value) return
  busy.value = true
  try { await api('/auth/logout', { method: 'POST', body: {} }); profile.value = null; closeModal(); toast('로그아웃했어요.') }
  catch (e) { toast(e.message) }
  finally { busy.value = false }
}
async function route() {
  closeModal()
  isTickets.value = location.hash === '#my-tickets'
  document.title = isTickets.value ? '마이티킷 — TIKIT' : 'TIKIT 티킷 — 취향이 만나는 순간'
  window.scrollTo({ top: 0, behavior: 'instant' })
  await nextTick()
  if (isTickets.value) document.getElementById('ticketsHeading')?.focus({ preventScroll: true })
}
function goHome() {
  if (location.hash) history.pushState(null, '', location.pathname + location.search)
  route()
}
function openTickets() {
  closeModal()
  if (location.hash !== '#my-tickets') location.hash = 'my-tickets'
  else { revision.value++; route() }
}
async function chooseCategory(value) {
  goHome()
  category.value = value
  expanded.value = false
  await nextTick()
  document.getElementById('performances')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
async function submitSearch() {
  goHome()
  search.value = searchInput.value.trim()
  expanded.value = true
  await nextTick()
  document.getElementById('performances')?.scrollIntoView({ behavior: 'smooth' })
}
function toggleFavorite(id) {
  favorites.value = favorites.value.includes(id) ? favorites.value.filter(value => value !== id) : [...favorites.value, id]
  try { localStorage.setItem('tikit.db.favorites', JSON.stringify(favorites.value)); toast(favorites.value.includes(id) ? '좋아하는 공연에 담았어요. 마이티킷에서 확인하세요.' : '찜한 공연에서 해제했어요.') }
  catch { toast('찜 목록을 브라우저에 저장할 수 없습니다.') }
}
function openBooking(id) {
  const show = shows.value.find(show => show.id === id)
  if (!show) return
  bookingConfirmation.value = false
  if (profile.value?.consent) {
    for (const type of ['performance_view', 'booking_started']) api('/events', { method: 'POST', body: { type, performanceId: id } }).catch(() => toast('탐색 기록 저장에 실패했습니다. 예매 내역은 별도로 저장됩니다.'))
  }
  booking.value = { showId: id, date: availableDates(show)[0], slot: show.slots[0], premium: 0, quantity: 1, requestKey: crypto.randomUUID() }
  openModal('booking', '공연 예매')
}
function loginForBooking() {
  openAuth('login', () => {
    bookingConfirmation.value = true
    openModal('booking', '예매 확인')
  })
}
function confirmCancel(order) { cancelOrder.value = order; openModal('cancel', '예매 취소 확인') }
async function changeOrder(id, action, done) {
  if (busy.value) { done?.(); return }
  const startedOnPage = isTickets.value
  busy.value = true
  try {
    await api(`/reservations/${id}/${action}`, { method: 'POST', body: {} })
    toast(action === 'cancel' ? '예매가 취소되었습니다.' : '결제가 완료되었습니다.')
    closeModal()
    revision.value++
    if (!startedOnPage) openTickets()
  } catch (e) { toast(e.message) }
  finally { busy.value = false; done?.() }
}
function openTaste() {
  if (!profile.value) { openAuth('signup', openTaste); return }
  openModal('taste', '나를 닮은 취향의 발견')
}
function showInfo(key) { infoKey.value = key; openModal('info', info[key][0]) }
onMounted(() => { initialize(); route(); window.addEventListener('hashchange', route); window.addEventListener('popstate', route) })
onBeforeUnmount(() => { clearTimeout(toastTimer); window.removeEventListener('hashchange', route); window.removeEventListener('popstate', route) })
</script>

<template>
  <div class="announcement">나를 닮은 공연을 만나는 새로운 방법 <span>MBTI로 취향 발견하기 ↗</span></div>
  <header><div class="header-main wrap">
    <a href="#" class="logo" aria-label="티킷 홈" @click.prevent="goHome">ti<span>k</span>it<span class="logo-dot">.</span></a>
    <form id="searchForm" class="search" @submit.prevent="submitSearch"><input id="searchInput" v-model="searchInput" type="search" placeholder="어떤 설렘을 찾고 있나요?" aria-label="공연 검색" @input="!searchInput && (search = '')"><button aria-label="검색" type="submit"><svg viewBox="0 0 24 24"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/></svg></button></form>
    <div class="account"><button id="loginButton" @click="profile ? openTaste() : openAuth('login')">{{ profile ? `${profile.name}님` : '로그인' }}</button><span></span><button id="signupButton" :disabled="busy" @click="signupOrLogout">{{ profile ? '로그아웃' : '회원가입' }}</button><button id="ticketsButton" class="my-ticket" :aria-current="isTickets ? 'page' : undefined" @click="openTickets"><svg viewBox="0 0 24 24"><path d="M4 5h16v5a2 2 0 0 0 0 4v5H4v-5a2 2 0 0 0 0-4Z"/><path d="M15 5v3m0 3v2m0 3v3"/></svg> 마이티킷</button></div>
  </div><nav class="wrap nav"><div id="genreNav" class="genre-nav"><button v-for="c in categories" :key="c" :data-category="c" :class="{ active: !isTickets && c === category }" :aria-pressed="!isTickets && c === category" @click="chooseCategory(c)">{{ c === '전체' ? '홈' : c }}</button></div><button id="tasteButton" class="taste-nav" @click="openTaste"><span>✦</span> MBTI 취향 찾기 <span class="new">NEW</span></button></nav></header>

  <div v-if="loading" class="tickets-loading wrap" role="status">공연 정보를 불러오는 중입니다…</div>
  <div v-else-if="loadError" class="tickets-empty wrap"><h1>서버에 연결하지 못했어요</h1><p role="alert">{{ loadError }}</p><button class="primary" @click="initialize">다시 시도하기</button></div>
  <template v-else>
    <HomePage v-show="!isTickets" :shows="shows" :favorites="favorites" :category="category" :search="search" :expanded="expanded" @category="chooseCategory" @show="openBooking" @favorite="toggleFavorite" @taste="openTaste" @expand="expanded = !expanded" />
    <TicketsPage v-if="isTickets" :profile="profile" :shows="shows" :favorites="favorites" :revision="revision" :busy="busy" @login="openAuth('login')" @signup="openAuth('signup')" @show="openBooking" @complete="id => changeOrder(id, 'complete')" @cancel="confirmCancel" />
  </template>

  <footer><div class="wrap footer-main"><a href="#" class="logo" @click.prevent="goHome">tikit.</a><div><div class="footer-links"><button data-info="about" @click="showInfo('about')">서비스 소개</button><button data-info="terms" @click="showInfo('terms')">이용약관</button><button data-info="privacy" @click="showInfo('privacy')"><b>개인정보 처리 안내</b></button><button data-info="help" @click="showInfo('help')">고객센터</button></div><p>취향이 만나는 순간, 티킷 · TIKIT</p><p class="muted">좋아하는 공연을 발견하고, 설레는 순간을 함께하세요.</p><small>© 2026 TIKIT. All moments reserved.</small></div><span class="footer-note">FIND YOUR NEXT<br><em>FAVORITE MOMENT.</em></span></div></footer>

  <ModalDialog v-if="modal" :title="modalTitle" @close="closeModal">
    <AuthForm v-if="modal === 'login' || modal === 'signup'" :key="modal" :mode="modal" @authenticated="authenticated" @switch="mode => openAuth(mode, authAfter)" />
    <BookingPanel v-else-if="modal === 'booking'" :show="selectedShow" :booking="booking" :profile="profile" :confirmation="bookingConfirmation" @title="title => modalTitle = title" @login="loginForBooking" @tickets="openTickets" @pay="(id, done) => changeOrder(id, 'complete', done)" @close="closeModal" @toast="toast" />
    <template v-else-if="modal === 'cancel'"><p class="modal-intro">{{ cancelOrder.performanceTitle }}<br>{{ cancelOrder.performanceDate }} {{ cancelOrder.sessionTime }} · {{ cancelOrder.quantity }}매<br>이 공연의 예매를 취소하시겠어요?</p><button id="confirmCancel" class="primary" :disabled="busy" @click="changeOrder(cancelOrder.id, 'cancel')">예매 취소하기</button><button class="secondary" :disabled="busy" @click="closeModal">돌아가기</button></template>
    <template v-else-if="modal === 'taste' && profile"><span class="tag">{{ profile.mbti }} · {{ profile.name }}님의 취향 탐색</span><h3>{{ profile.mbti.includes('E') ? '함께 열광하는 라이브의 에너지' : '마음에 오래 남는 나만의 감상' }}</h3><p class="modal-intro">새로운 공연 취향을 발견해 보세요. MBTI만으로 취향이 정해지지는 않아요. 다양한 장르를 자유롭게 탐색해 주세요.</p><div class="taste-cards"><div v-for="c in tasteCategories" :key="c" class="taste-card"><b>{{ c }}</b><p>{{ tasteText[c] }}</p><button class="text-link" :data-taste-category="c" @click="chooseCategory(c)">{{ c }} 둘러보기 ↗</button></div></div><div class="notice">현재 추천은 MBTI의 E/I에 따른 탐색 예시입니다. 실제 사용자별 선호 통계가 아닙니다. 수집한 공연 조회와 예매 기록은 향후 취향 분석에 활용할 수 있습니다.</div></template>
    <template v-else-if="modal === 'info'"><p class="modal-intro">{{ info[infoKey][1] }}</p><button class="primary" @click="closeModal">확인</button></template>
  </ModalDialog>
  <div id="toast" :class="{ show: toastMessage }" role="status" aria-live="polite">{{ toastMessage }}</div>
</template>
