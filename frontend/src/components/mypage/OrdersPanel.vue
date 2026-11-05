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

// 마이페이지 예매·결제 내역
// 로그인이 필요한 화면이라 router에서 비로그인 사용자를 로그인 화면으로 보냅니다.
const router = useRouter();
const auth = useAuthStore();
const authed = useAuthedApi();
const reservations = useReservations();

const orders = ref([]);
const legacyOrders = ref([]); // 이전 방식(즉시 모의 결제, /orders)으로 저장된 내역
const shows = ref([]);
const loading = ref(true);
const error = ref('');
const busy = ref(false);
const modal = ref(null); // { type: 'cancel', order }
const heading = ref(null);

const showById = computed(() => Object.fromEntries(shows.value.map(s => [s.id, s])));

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const [list, legacy, all] = await Promise.all([
      reservations.list(),
      authed('/orders').catch(() => []),
      auth.api('/performances').catch(() => []),
    ]);
    orders.value = list;
    legacyOrders.value = legacy;
    shows.value = all;
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

onMounted(() => {
  heading.value?.focus({ preventScroll: true });
  load();
});
</script>

<template>
  <section class="orders-panel" aria-labelledby="ticketsHeading">
      <div class="panel-head">
        <div class="section-kicker">RESERVATIONS</div>
        <h2 id="ticketsHeading" ref="heading" tabindex="-1">예매 내역</h2>
        <p class="modal-intro">예매한 공연과 결제 내역을 한곳에서 확인하세요.</p>
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

        </template>
      </div>
  </section>

  <BaseModal v-if="modal?.type === 'cancel'" title="예매 취소 확인" @close="modal = null">
    <p class="modal-intro">
      {{ modal.order.performance_title }}<br>{{ modal.order.performance_date }} {{ modal.order.session_time }} · {{ modal.order.quantity }}매<br>
      이 공연의 예매를 취소하시겠어요? {{ modal.order.payment_status === 'COMPLETED' ? '결제도 함께 취소됩니다.' : '' }}
    </p>
    <button class="primary" type="button" :disabled="busy" @click="cancel(modal.order)">예매 취소하기</button>
    <button class="secondary" type="button" :disabled="busy" @click="modal = null">돌아가기</button>
  </BaseModal>
</template>

<style scoped>
.orders-panel { container-type: inline-size; }
#ticketsHeading:focus { outline: none; }
@container (max-width: 680px) {
  .ticket-card { grid-template-columns: 76px minmax(0, 1fr); gap: 16px; padding: 18px; }
  :deep(.ticket-poster .poster) { width: 76px; padding: 8px; }
  :deep(.ticket-poster .poster-title) { font-size: 17px; }
  :deep(.ticket-payment) { grid-column: 1 / -1; border-left: 0; border-top: 1px solid var(--line); padding: 16px 0 0; }
  .tickets-list-heading { align-items: flex-start; flex-direction: column; gap: 8px; }
  .ticket-favorites > div { grid-template-columns: 1fr; }
}
</style>
