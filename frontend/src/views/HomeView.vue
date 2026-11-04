<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import HeroSlider from '@/components/HeroSlider.vue';
import PerformanceCard from '@/components/PerformanceCard.vue';
import RankingList from '@/components/RankingList.vue';
import CategoryIcon from '@/components/CategoryIcon.vue';
import BookingModal from '@/components/BookingModal.vue';
import TasteModal from '@/components/TasteModal.vue';
import { useAuthStore } from '@/stores/auth';
import { useAuthedApi } from '@/composables/useAuthedApi';
import { toast } from '@/composables/useToast';
import { CATEGORIES, PENDING_BOOKING_KEY, loginRoute, session } from '@/utils';

// 메인 화면: 배너, 카테고리, 공연 목록, 랭킹, 예매·취향(모달). 마이티킷은 /my-tickets 화면입니다.
// 검색어·카테고리·정렬은 주소(?q= / ?category= / ?sort=)에 들어 있어 로그인 후 돌아와도 같은 화면이 됩니다.
const SORTS = [{ id: 'popular', label: '인기순' }, { id: 'date', label: '공연일순' }, { id: 'price', label: '낮은 가격순' }];

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const authed = useAuthedApi();

const allShows = ref([]);
const listShows = ref([]);
const ranking = ref([]);
const favorites = ref([]);
const expanded = ref(false);
const modal = ref(null);
const performancesEl = ref(null);

/* ---------- 주소(URL) 상태 ---------- */
const category = computed(() => (CATEGORIES.includes(route.query.category) ? route.query.category : '전체'));
const search = computed(() => (typeof route.query.q === 'string' ? route.query.q.trim().slice(0, 100) : ''));
const sort = computed({
  get: () => (SORTS.some(s => s.id === route.query.sort) ? route.query.sort : 'popular'),
  set: value => router.replace({ query: { ...route.query, sort: value === 'popular' ? undefined : value } }),
});

function chooseCategory(c) {
  router.push({ path: '/', query: c === '전체' ? {} : { category: c } });
}
function seeAll() {
  expanded.value = true;
  router.push('/');
}
const scrollToList = () => nextTick(() => performancesEl.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }));

/* ---------- 공연 목록 ---------- */
const visibleShows = computed(() => (expanded.value ? listShows.value : listShows.value.slice(0, 4)));
const listTitle = computed(() => {
  if (search.value) return `“${search.value}” 검색 결과`;
  return category.value === '전체' ? '지금, 가장 설레는 공연' : `${category.value}, 나의 다음 설렘`;
});

let listRequest = 0;
async function loadList() {
  const id = ++listRequest;
  const params = new URLSearchParams({ sort: sort.value });
  if (category.value !== '전체') params.set('category', category.value);
  if (search.value) params.set('q', search.value);
  try {
    const result = await auth.api(`/performances?${params}`);
    if (id === listRequest) listShows.value = result; // 가장 늦게 보낸 요청의 결과만 반영
  } catch (err) {
    if (id === listRequest) toast(err.message);
  }
}

// 카테고리를 바꾸면 접고, 검색하면 펼쳐서 보여줍니다.
watch([category, search], ([c, q], [oldC, oldQ]) => {
  if (c !== oldC) expanded.value = false;
  if (q && q !== oldQ) expanded.value = true;
  scrollToList();
});
watch([category, search, sort], loadList);

async function loadRanking() {
  try { ranking.value = await auth.api('/performances/ranking?limit=50'); } catch { /* 랭킹은 실패해도 화면은 계속 사용 */ }
}

/* ---------- 찜 ---------- */
async function loadFavorites() {
  if (!auth.profile) { favorites.value = []; return; }
  try { favorites.value = await auth.api('/favorites'); } catch { favorites.value = []; }
}
watch(() => auth.profile?.id, loadFavorites);

async function toggleFavorite(id) {
  if (!auth.profile) { router.push(loginRoute(route.fullPath)); return; }
  const saved = favorites.value.includes(id);
  try {
    await authed(`/favorites/${encodeURIComponent(id)}`, { method: saved ? 'DELETE' : 'PUT' });
    favorites.value = saved ? favorites.value.filter(x => x !== id) : [...favorites.value, id];
    toast(saved ? '찜한 공연에서 해제했어요.' : '좋아하는 공연에 담았어요. 마이티킷에서 확인하세요.');
  } catch (err) {
    toast(err.message);
  }
}

/* ---------- 모달 ---------- */
// 모달을 닫으면 열기 전에 누른 버튼으로 포커스를 돌려줍니다.
let returnFocus = null;
watch(modal, (now, before) => {
  if (now && !before) returnFocus = document.activeElement;
  if (!now && before) nextTick(() => returnFocus?.focus?.());
});
const closeModal = () => { modal.value = null; };

async function openBooking(id, { saved = {}, startAtConfirm = false, track = true } = {}) {
  let show;
  try {
    show = await auth.api(`/performances/${encodeURIComponent(id)}`);
  } catch (err) {
    toast(err.message);
    return;
  }
  // 조회 기록은 실패해도 예매 흐름에 영향을 주지 않습니다.
  if (track) auth.api('/events', { method: 'POST', body: { performance_id: id } }).catch(() => {});
  modal.value = { type: 'booking', show, saved, startAtConfirm };
}

// 예매 내역은 마이티킷 화면에서 확인합니다 (로그인하지 않았으면 router가 로그인 화면으로 보냄).
const openOrders = () => router.push('/my-tickets');

function openTaste() {
  if (!auth.profile) { router.push(loginRoute('/?open=taste')); return; }
  modal.value = { type: 'taste' };
}
function chooseTaste(c) {
  closeModal();
  chooseCategory(c);
}

// ?open=mytikit|taste, ?resume=booking, ?show=<공연 id> 는 한 번만 처리하고 주소에서 지웁니다.
async function handleOneShot() {
  const { open, resume, show, ...rest } = route.query;
  if (!open && !resume && !show) return;
  if (open === 'mytikit') { router.replace('/my-tickets'); return; } // 이전 주소 호환
  router.replace({ query: rest });
  try { await auth.restore(); } catch { /* 아래에서 로그인 여부로 처리 */ }
  if (typeof show === 'string') openBooking(show);
  if (open === 'taste') openTaste();
  if (resume === 'booking') {
    let saved = null;
    try { saved = JSON.parse(session.take(PENDING_BOOKING_KEY)); } catch { /* 무시 */ }
    if (saved?.showId) openBooking(saved.showId, { saved, startAtConfirm: true, track: false });
  }
}
watch(() => [route.query.open, route.query.resume, route.query.show], handleOneShot);

/* ---------- 시작 ---------- */
onMounted(async () => {
  expanded.value = Boolean(search.value);
  try { await auth.restore(); } catch { /* App에서 알림 */ }
  const [shows] = await Promise.all([
    auth.api('/performances').catch(err => { toast(err.message); return []; }),
    loadFavorites(),
    loadList(),
  ]);
  allShows.value = shows;
  loadRanking();
  handleOneShot();
});
</script>

<template>
  <main>
    <HeroSlider :shows="allShows" @open="openBooking" />

    <section class="quick-categories wrap" aria-label="공연 카테고리 바로가기">
      <button v-for="c in CATEGORIES.slice(1)" :key="c" type="button" class="quick-category" @click="chooseCategory(c)">
        <span class="category-icon"><CategoryIcon :category="c" /></span>{{ c }}
      </button>
    </section>

    <section id="performances" ref="performancesEl" class="section wrap">
      <div class="section-head">
        <div><div class="section-kicker">YOUR NEXT MOMENT</div><h2>{{ listTitle }} <span>✦</span></h2></div>
        <button class="text-link" type="button" @click="seeAll">전체보기 ↗</button>
      </div>
      <div class="filter-row">
        <div class="chips">
          <button
            v-for="c in CATEGORIES" :key="c" type="button" class="chip"
            :class="{ active: c === category }" :aria-pressed="String(c === category)" @click="chooseCategory(c)"
          >{{ c }}</button>
        </div>
        <select v-model="sort" aria-label="공연 정렬">
          <option v-for="s in SORTS" :key="s.id" :value="s.id">{{ s.label }}</option>
        </select>
      </div>
      <div class="performance-grid" aria-live="polite">
        <PerformanceCard
          v-for="s in visibleShows" :key="s.id" :show="s" :saved="favorites.includes(s.id)"
          @open="openBooking" @favorite="toggleFavorite"
        />
      </div>
      <div v-if="!listShows.length" class="empty">검색 결과가 없어요.<br><small>다른 공연명이나 장소로 검색해 보세요.</small></div>
      <button v-if="listShows.length > 4" class="more-button" type="button" @click="expanded = !expanded">
        <template v-if="expanded">간략히 보기 <span>−</span></template>
        <template v-else>더 많은 설렘 만나보기 <span>＋</span></template>
      </button>
    </section>

    <section class="mbti-banner wrap">
      <div class="mbti-symbols"><span>ENFP</span><span>✳</span><span>INTJ</span><span>✦</span></div>
      <div class="mbti-copy"><span class="section-kicker">A LITTLE MORE YOU</span><h2>같은 MBTI는, 어떤 공연을 좋아할까?</h2><p>나를 닮은 사람들의 취향에서 새로운 인생 공연을 발견해 보세요.</p></div>
      <button type="button" @click="openTaste">내 취향 찾으러 가기 <span>↗</span></button>
    </section>

    <RankingList :ranking="ranking" @open="openBooking" />

    <section class="service-strip wrap">
      <div><b>좋아하는 순간을 놓치지 않도록.</b><p>당신의 다음 설렘도 티킷과 함께하세요.</p></div>
      <div><span>✧ 취향을 발견하고</span><span>♡ 좋아함을 모으고</span><span>↗ 새로운 순간으로</span></div>
    </section>
  </main>

  <BookingModal
    v-if="modal?.type === 'booking'" :key="modal.show.id" :show="modal.show" :saved="modal.saved" :start-at-confirm="modal.startAtConfirm"
    @close="closeModal" @paid="loadRanking" @view-orders="openOrders"
  />
  <TasteModal v-else-if="modal?.type === 'taste'" @close="closeModal" @choose="chooseTaste" />
</template>
