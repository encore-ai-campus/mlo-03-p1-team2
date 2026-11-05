<script setup>
import { computed, onMounted, ref } from 'vue';
import PanelHead from './PanelHead.vue';
import { useAuthedApi } from '@/composables/useAuthedApi';
import { track } from '@/utils/tracker';

const authed = useAuthedApi();
const report = ref(null);
const loading = ref(true);
const error = ref('');
const total = computed(() => report.value ? Object.values(report.value.totals).reduce((sum, n) => sum + n, 0) : 0);
const ranked = computed(() => [...(report.value?.categories || [])].sort((a, b) => score(b) - score(a)));
const peers = computed(() => [...(report.value?.categories || [])].filter(c => c.peer_favorites > 0).sort((a, b) => b.peer_favorites - a.peer_favorites));
const score = c => c.views + c.favorites + c.bookings;

async function load() {
  loading.value = true;
  error.value = '';
  try {
    report.value = await authed('/users/me/taste-report');
    track('taste_view', { source: 'mypage' });
  }
  catch (err) { error.value = err.message; }
  finally { loading.value = false; }
}
onMounted(load);
</script>

<template>
  <PanelHead kicker="MY TASTE" title="MBTI 취향 리포트" intro="나의 공연 탐색 기록과 같은 MBTI 관객의 찜을 함께 살펴보세요." />
  <p v-if="loading" class="tickets-loading" role="status">취향 리포트를 분석하고 있어요…</p>
  <div v-else-if="error" class="tickets-empty">
    <p role="alert">{{ error }}</p><button class="secondary" type="button" @click="load">다시 불러오기</button>
  </div>
  <template v-else-if="report">
    <span class="tag taste-profile">{{ report.mbti }} · 나의 공연 취향</span>
    <section v-if="total" class="report-section">
      <h3>내가 관심을 보인 장르</h3>
      <div v-for="item in ranked" :key="item.category" class="genre-row">
        <RouterLink :to="{ path: '/', query: { category: item.category } }">{{ item.category }} ↗</RouterLink>
        <progress :value="score(item)" :max="total" :aria-label="`${item.category} 관심 기록`" />
        <span>{{ Math.round(score(item) / total * 100) }}%</span>
        <small>조회 {{ item.views }} · 찜 {{ item.favorites }} · 예매 {{ item.bookings }}</small>
      </div>
      <p class="modal-intro">조회 횟수·현재 찜·완료 예매 건수를 합산한 비율이에요. 결제 대기와 취소 예매는 제외해요.</p>
    </section>
    <div v-else class="tickets-empty">
      <h3>나만의 취향을 쌓아 보세요</h3>
      <p>공연을 둘러보고 하트를 누르면 내 관심 장르를 확인할 수 있어요.</p>
      <RouterLink class="primary" to="/">공연 둘러보기</RouterLink>
    </div>
    <section class="report-section">
      <h3>같은 {{ report.mbti }} 관객이 찜한 장르</h3>
      <p class="modal-intro">나를 제외하고 찜한 공연이 있는 {{ report.peer_users }}명의 현재 기록이에요.</p>
      <ul v-if="peers.length" class="peer-list">
        <li v-for="item in peers" :key="item.category">
          <RouterLink :to="{ path: '/', query: { category: item.category } }">{{ item.category }} 둘러보기 ↗</RouterLink>
          <b>{{ item.peer_favorites }}개 찜</b>
        </li>
      </ul>
      <p v-else class="modal-intro">아직 같은 MBTI 관객의 찜 기록이 충분하지 않아요.</p>
    </section>
  </template>
</template>

<style scoped>
.taste-profile { font-size: 12px; font-weight: 800; padding: 5px 8px; }
.report-section { margin-top: 32px; } h3 { font-size: 17px; }
.genre-row { display: grid; grid-template-columns: 70px minmax(0, 1fr) 42px; align-items: center; gap: 8px; margin: 20px 0; font-size: 13px; }
progress { width: 100%; height: 10px; accent-color: var(--purple); }
.genre-row small { grid-column: 2 / -1; color: #7e718a; }
.peer-list { list-style: none; padding: 0; } .peer-list li { display: flex; justify-content: space-between; padding: 14px 0; border-bottom: 1px solid var(--line); font-size: 13px; }
</style>
