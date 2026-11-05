<script setup>
import { computed, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import BaseModal from './BaseModal.vue';
import PosterArt from './PosterArt.vue';
import { useAuthStore } from '@/stores/auth';
import { useReservations } from '@/composables/useReservations';
import { toast } from '@/composables/useToast';
import {
  MAX_QUANTITY, PAYMENT_LABELS, PENDING_BOOKING_KEY, PREMIUM_SURCHARGE,
  loginRoute, newRequestKey, seatLabel, session, won,
} from '@/utils';

// 예매 흐름: 01 날짜·회차 → 02 예매 확인(예매 요청) → 03 완료(결제 대기 → 결제하기)
const QUANTITIES = Array.from({ length: MAX_QUANTITY }, (_, i) => i + 1);
const RESUME_PATH = '/?resume=booking';

const props = defineProps({
  show: { type: Object, required: true },
  saved: { type: Object, default: () => ({}) }, // 로그인 후 돌아왔을 때 이전 선택값
  startAtConfirm: { type: Boolean, default: false },
});
const emit = defineEmits(['close', 'booked', 'paid', 'view-orders']);

const auth = useAuthStore();
const reservations = useReservations();
const router = useRouter();

const s = props.show;
const saved = props.saved || {};
const booking = reactive({
  date: s.available_dates.includes(saved.date) ? saved.date : s.available_dates[0],
  slot: s.slots.includes(saved.slot) ? saved.slot : s.slots[0],
  premium: saved.premium === PREMIUM_SURCHARGE ? PREMIUM_SURCHARGE : 0,
  quantity: QUANTITIES.includes(saved.quantity) ? saved.quantity : 1,
  // 예매 확인 단계에 들어올 때마다 새로 만들어, 같은 확인 화면의 재시도만 같은 예매로 처리합니다.
  requestKey: newRequestKey(),
});
const step = ref(props.startAtConfirm && auth.profile ? 'confirm' : 'select');
const titles = { select: '설렘을 예약하는 시간', confirm: '예매 확인', done: '예매 완료' };

const total = computed(() => (s.price + booking.premium) * booking.quantity);
const weekday = iso => ['일', '월', '화', '수', '목', '금', '토'][new Date(`${iso}T12:00:00`).getDay()];
const shortDate = iso => { const [, m, d] = iso.split('-'); return `${Number(m)}.${d}`; };

/* ---------- 01 → 02 ---------- */
function goConfirm() {
  if (!auth.profile) {
    // 로그인 화면에 다녀와도 선택한 날짜·회차가 유지되도록 현재 탭에 잠시 보관합니다.
    const { requestKey, ...selection } = booking;
    session.set(PENDING_BOOKING_KEY, JSON.stringify({ showId: s.id, ...selection }));
    router.push(loginRoute(RESUME_PATH));
    return;
  }
  // 예매 시작 기록(분석용). 실패해도 예매에는 영향이 없습니다.
  auth.api('/events', { method: 'POST', body: { performance_id: s.id, type: 'booking_started' } }).catch(() => {});
  step.value = 'confirm';
}
function backToSelect() {
  booking.requestKey = newRequestKey();
  agreed.value = false;
  error.value = '';
  step.value = 'select';
}

/* ---------- 02 예매 요청 ---------- */
const agreed = ref(false);
const error = ref('');
const busy = ref(false);
const order = ref(null);

async function reserve() {
  if (busy.value) return;
  if (!agreed.value) { error.value = '예매 내용을 확인하고 동의해 주세요.'; return; }
  busy.value = true;
  error.value = '';
  try {
    order.value = await reservations.create({ show: s, ...booking }, RESUME_PATH);
    step.value = 'done';
    emit('booked', order.value);
    toast('예매가 완료되었습니다. 결제를 진행해 주세요.');
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

/* ---------- 03 모의 결제 ---------- */
async function pay() {
  if (busy.value) return;
  busy.value = true;
  try {
    order.value = await reservations.complete(order.value.id, '/mypage/orders');
    emit('paid', order.value);
    toast('결제가 완료되었습니다.');
  } catch (err) {
    toast(err.message);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <BaseModal :title="titles[step]" @close="emit('close')">
    <template v-if="step !== 'done'">
      <div class="booking-steps">
        <span :class="{ current: step === 'select' }">01 날짜 · 회차</span><span>──</span>
        <span :class="{ current: step === 'confirm' }">02 예매 확인</span><span>──</span><span>03 완료</span>
      </div>
      <div class="detail-top">
        <PosterArt :show="s" />
        <div>
          <span class="tag">{{ s.category }}</span><h3>{{ s.title }}</h3>
          <p>{{ s.venue }}</p><p>{{ s.date_label }}</p><p>시연 공연 · 만 7세 이상 · 약 120분</p>
        </div>
      </div>
    </template>

    <!-- 01 날짜 · 회차 -->
    <template v-if="step === 'select'">
      <p class="field-title">관람 날짜 선택</p>
      <div class="date-options">
        <button
          v-for="d in s.available_dates" :key="d" type="button" class="date-option"
          :class="{ selected: booking.date === d }" :aria-pressed="String(booking.date === d)" @click="booking.date = d"
        ><small>{{ weekday(d) }}</small>{{ shortDate(d) }}</button>
      </div>
      <p class="field-title">회차 선택</p>
      <div class="slot-options">
        <button
          v-for="t in s.slots" :key="t" type="button" class="slot-option"
          :class="{ selected: booking.slot === t }" :aria-pressed="String(booking.slot === t)" @click="booking.slot = t"
        >{{ t }}</button>
      </div>
      <div class="seat-quantity">
        <label><p class="field-title">좌석 등급</p>
          <select v-model.number="booking.premium">
            <option :value="0">일반석 · {{ won(s.price) }}</option>
            <option :value="PREMIUM_SURCHARGE">프리미엄석 · {{ won(s.price + PREMIUM_SURCHARGE) }}</option>
          </select>
        </label>
        <label><p class="field-title">예매 수량</p>
          <select v-model.number="booking.quantity"><option v-for="n in QUANTITIES" :key="n" :value="n">{{ n }}매</option></select>
        </label>
      </div>
      <div class="summary-box">
        <div class="summary-line"><span>티켓 금액</span><span>{{ won(total) }}</span></div>
        <div class="summary-line"><span>예매 수수료</span><span>0원</span></div>
        <div class="summary-line total"><span>총 결제 금액</span><b>{{ won(total) }}</b></div>
      </div>
      <button class="primary" type="button" @click="goConfirm">{{ auth.profile ? '예매하기' : '로그인 후 예매하기 →' }}</button>
    </template>

    <!-- 02 예매 확인 -->
    <template v-else-if="step === 'confirm'">
      <div class="summary-box">
        <div class="summary-line"><span>예매자 / MBTI</span><span>{{ auth.profile?.name }} / {{ auth.profile?.mbti }}</span></div>
        <div class="summary-line"><span>관람 일시</span><span>{{ booking.date }} {{ booking.slot }}</span></div>
        <div class="summary-line"><span>좌석 / 수량</span><span>{{ booking.premium ? '프리미엄석' : '일반석' }} / {{ booking.quantity }}매</span></div>
        <div class="summary-line total"><span>결제 예정 금액</span><b>{{ won(total) }}</b></div>
      </div>
      <p class="modal-intro">예매 내용을 확인해 주세요. 예매 후 결제를 진행할 수 있어요.</p>
      <form @submit.prevent="reserve">
        <label class="check-label"><input v-model="agreed" type="checkbox" required @change="error = ''"><span>공연·날짜·회차·금액을 확인했으며 예매에 동의합니다.</span></label>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="primary" type="submit" :disabled="busy">{{ busy ? '예매 중…' : `예매하기 · ${won(total)}` }}</button>
      </form>
      <button class="secondary" type="button" :disabled="busy" @click="backToSelect">← 날짜·회차 다시 선택</button>
    </template>

    <!-- 03 완료 -->
    <template v-else>
      <div class="success">
        <div class="success-icon">✓</div>
        <h3>{{ order.payment_status === 'COMPLETED' ? '결제까지 모두 끝났어요!' : '설레는 순간을 예약했어요!' }}</h3>
        <p>{{ order.performance_title }}<br>{{ order.performance_date }} {{ order.session_time }} · {{ seatLabel(order.seat_grade) }} {{ order.quantity }}매</p>
        <span class="order-status" :class="`status-${order.payment_status.toLowerCase()}`">{{ PAYMENT_LABELS[order.payment_status] }}</span>
        <p>{{ order.payment_status === 'COMPLETED' ? '결제 금액' : '결제 예정 금액' }} {{ won(order.amount) }}<br>마이페이지의 예매 내역에서 확인할 수 있어요.</p>
      </div>
      <div class="demo-note">실제 결제·환불·티켓 발급은 발생하지 않는 모의 결제입니다.</div>
      <button v-if="order.payment_status === 'PENDING'" class="primary" type="button" :disabled="busy" @click="pay">
        {{ busy ? '결제 처리 중…' : `${won(order.amount)} 결제하기` }}
      </button>
      <button class="secondary" type="button" @click="emit('view-orders')">예매 내역 확인하기</button>
      <button class="secondary" type="button" @click="emit('close')">다른 공연 둘러보기</button>
    </template>
  </BaseModal>
</template>
