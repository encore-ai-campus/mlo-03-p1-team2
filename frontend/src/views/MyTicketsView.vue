<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import BaseModal from '@/components/BaseModal.vue';
import TicketCard from '@/components/TicketCard.vue';
import { useAuthStore } from '@/stores/auth';
import { useAuthedApi } from '@/composables/useAuthedApi';
import { useReservations } from '@/composables/useReservations';
import { toast } from '@/composables/useToast';
import { won } from '@/utils';

// 마이티킷: 예매·결제 내역(결제하기·예매 취소), 찜한 공연, 내 데이터 내려받기·삭제
// 로그인이 필요한 화면이라 router에서 비로그인 사용자를 로그인 화면으로 보냅니다.
const router = useRouter();
const auth = useAuthStore();
const authed = useAuthedApi();
const reservations = useReservations();

const orders = ref([]);
const legacyOrders = ref([]); // 이전 방식(즉시 모의 결제, /orders)으로 저장된 내역
const shows = ref([]);
const favorites = ref([]);
const loading = ref(true);
const error = ref('');
const busy = ref(false);
const modal = ref(null); // { type: 'cancel', order } | { type: 'delete' }
const heading = ref(null);

const showById = computed(() => Object.fromEntries(shows.value.map(s => [s.id, s])));
const liked = computed(() => shows.value.filter(s => favorites.value.includes(s.id)));

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const [list, legacy, all, favs] = await Promise.all([
      reservations.list(),
      authed('/orders').catch(() => []),
      auth.api('/performances').catch(() => []),
      authed('/favorites').catch(() => []),
    ]);
    orders.value = list;
    legacyOrders.value = legacy;
    shows.value = all;
    favorites.value = favs;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

// 결제·취소 후 서버가 돌려준 최신 예매로 목록의 해당 건을 바꿉니다.
function replace(updated) {
  orders.value = orders.value.map(o => (o.id === updated.id ? updated : o));
}

async function complete(order) {
  if (busy.value) return;
  busy.value = true;
  try {
    replace(await reservations.complete(order.id));
    toast('결제가 완료되었습니다.');
  } catch (err) {
    toast(err.message);
  } finally {
    busy.value = false;
  }
}

async function cancel(order) {
  if (busy.value) return;
  busy.value = true;
  try {
    replace(await reservations.cancel(order.id));
    modal.value = null;
    toast('예매가 취소되었습니다.');
  } catch (err) {
    toast(err.message);
  } finally {
    busy.value = false;
  }
}

const openShow = id => router.push({ path: '/', query: { show: id } });

/* ---------- 내 데이터 ---------- */
async function exportData() {
  try {
    const payload = await authed('/users/me/export');
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a');
    a.href = url; a.download = 'tikit-my-data.json'; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast('데이터를 내려받았어요.');
  } catch (err) { toast(err.message); }
}

async function deleteAccount() {
  busy.value = true;
  try {
    await authed('/users/me', { method: 'DELETE' });
    auth.logout();
    modal.value = null;
    router.push('/');
    toast('계정과 연결된 데이터를 삭제했어요.');
  } catch (err) {
    toast(err.message);
  } finally {
    busy.value = false;
  }
}

onMounted(() => {
  heading.value?.focus({ preventScroll: true });
  load();
});
</script>

<template>
  <main class="tickets-page" aria-labelledby="ticketsHeading">
    <section class="tickets-shell wrap">
      <RouterLink to="/" class="tickets-back">← 공연 둘러보기</RouterLink>
      <div class="tickets-heading">
        <div class="section-kicker">MY TIKIT</div>
        <h1 id="ticketsHeading" ref="heading" tabindex="-1">마이티킷</h1>
        <p>예매한 공연과 결제 내역을 한곳에서 확인하세요.</p>
      </div>

      <div aria-live="polite" :aria-busy="String(loading)">
        <p v-if="loading" class="tickets-loading" role="status">예매 내역을 불러오는 중입니다…</p>
        <div v-else-if="error" class="tickets-empty">
          <h2>내역을 불러오지 못했어요</h2>
          <p role="alert">{{ error }}</p>
          <button class="primary" type="button" @click="load">다시 조회하기</button>
        </div>
        <template v-else>
          <div class="tickets-list-heading">
            <h2>나의 예매 <span>{{ orders.length }}</span></h2>
            <p>{{ auth.profile?.name }}님의 설레는 순간들</p>
          </div>
          <div class="tickets-list">
            <TicketCard
              v-for="o in orders" :key="o.id" :order="o" :show="showById[o.performance_id]" :busy="busy"
              @open-show="openShow" @complete="complete" @cancel="order => (modal = { type: 'cancel', order })"
            />
            <div v-if="!orders.length" class="tickets-empty">
              <span class="tickets-empty-icon" aria-hidden="true">✦</span>
              <h2>아직 예매한 공연이 없어요</h2>
              <p>마음에 드는 공연을 찾아 새로운 설렘을 시작해 보세요.</p>
              <RouterLink class="primary" to="/">공연 둘러보기 ↗</RouterLink>
            </div>
          </div>

          <section v-if="legacyOrders.length" class="ticket-favorites">
            <h2>이전 모의 예매 <span>{{ legacyOrders.length }}</span></h2>
            <article v-for="o in legacyOrders" :key="o.id" class="order-card">
              <span class="order-status">모의 예매 완료 · 실제 결제 없음</span>
              <h3>{{ o.performance_title }}</h3>
              <p>{{ o.performance_date }} {{ o.session_time }} · {{ o.venue }}<br>{{ o.quantity }}매 · {{ won(o.amount) }}</p>
            </article>
          </section>

          <section v-if="liked.length" class="ticket-favorites">
            <h2>찜한 공연 <span>{{ liked.length }}</span></h2>
            <div>
              <button v-for="s in liked" :key="s.id" class="secondary" type="button" @click="openShow(s.id)">{{ s.title }} ↗</button>
            </div>
          </section>

          <section class="ticket-favorites">
            <h2>내 데이터</h2>
            <div>
              <button class="secondary" type="button" @click="exportData">내 취향·예매 데이터 내려받기 (JSON)</button>
              <button class="secondary" type="button" @click="modal = { type: 'delete' }">내 계정·취향·예매 데이터 삭제</button>
            </div>
          </section>
        </template>
      </div>
    </section>
  </main>

  <BaseModal v-if="modal?.type === 'cancel'" title="예매 취소 확인" @close="modal = null">
    <p class="modal-intro">
      {{ modal.order.performance_title }}<br>{{ modal.order.performance_date }} {{ modal.order.session_time }} · {{ modal.order.quantity }}매<br>
      이 공연의 예매를 취소하시겠어요? {{ modal.order.payment_status === 'COMPLETED' ? '결제도 함께 취소됩니다.' : '' }}
    </p>
    <button class="primary" type="button" :disabled="busy" @click="cancel(modal.order)">예매 취소하기</button>
    <button class="secondary" type="button" :disabled="busy" @click="modal = null">돌아가기</button>
  </BaseModal>
  <BaseModal v-else-if="modal?.type === 'delete'" title="내 데이터 삭제" @close="modal = null">
    <p class="modal-intro">계정과 연결된 공연 조회·찜·예매·결제 내역을 서버에서 삭제합니다. 삭제 후 복구할 수 없습니다.</p>
    <button class="primary" type="button" :disabled="busy" @click="deleteAccount">내 데이터 삭제하기</button>
    <button class="secondary" type="button" :disabled="busy" @click="modal = null">마이티킷으로 돌아가기</button>
  </BaseModal>
</template>
