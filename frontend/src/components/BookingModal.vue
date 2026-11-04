<script setup>
import { computed, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import BaseModal from './BaseModal.vue';
import PosterArt from './PosterArt.vue';
import { useAuthStore } from '@/stores/auth';
import { useAuthedApi } from '@/composables/useAuthedApi';
import { PENDING_BOOKING_KEY, loginRoute, session, won } from '@/utils';

// 예매 흐름: 01 날짜·회차 → 02 모의 결제 → 03 완료
const PREMIUM_SURCHARGE = 30000;
const PAYMENT_METHODS = ['간편결제', '신용카드', '계좌이체'];
const QUANTITIES = [1, 2, 3, 4];
const RESUME_PATH = '/?resume=booking';

const props = defineProps({
  show: { type: Object, required: true },
  saved: { type: Object, default: () => ({}) }, // 로그인 후 돌아왔을 때 이전 선택값
  startAtPayment: { type: Boolean, default: false },
});
const emit = defineEmits(['close', 'booked', 'view-orders']);

const auth = useAuthStore();
const authed = useAuthedApi();
const router = useRouter();

const s = props.show;
const saved = props.saved || {};
const booking = reactive({
  date: s.available_dates.includes(saved.date) ? saved.date : s.available_dates[0],
  slot: s.slots.includes(saved.slot) ? saved.slot : s.slots[0],
  premium: saved.premium === PREMIUM_SURCHARGE ? PREMIUM_SURCHARGE : 0,
  quantity: QUANTITIES.includes(saved.quantity) ? saved.quantity : 1,
  paymentMethod: PAYMENT_METHODS.includes(saved.paymentMethod) ? saved.paymentMethod : PAYMENT_METHODS[0],
});
const step = ref(props.startAtPayment && auth.profile ? 'payment' : 'select');
const titles = { select: '설렘을 예약하는 시간', payment: '모의 결제', done: '모의 예매 완료' };

const total = computed(() => (s.price + booking.premium) * booking.quantity);
const weekday = iso => ['일', '월', '화', '수', '목', '금', '토'][new Date(`${iso}T12:00:00`).getDay()];
const shortDate = iso => { const [, m, d] = iso.split('-'); return `${Number(m)}.${d}`; };

function goPayment() {
  if (auth.profile) { step.value = 'payment'; return; }
  // 로그인 화면에 다녀와도 선택한 날짜·회차가 유지되도록 현재 탭에 잠시 보관합니다.
  session.set(PENDING_BOOKING_KEY, JSON.stringify({ showId: s.id, ...booking }));
  router.push(loginRoute(RESUME_PATH));
}

/* ---------- 모의 결제 ---------- */
const agreed = ref(false);
const error = ref('');
const busy = ref(false);
const order = ref(null);

async function pay() {
  if (busy.value) return;
  if (!agreed.value) { error.value = '예매 내용을 확인하고 동의해 주세요.'; return; }
  busy.value = true;
  try {
    order.value = await authed('/orders', {
      method: 'POST',
      body: {
        performance_id: s.id, performance_date: booking.date, session_time: booking.slot,
        seat_grade: booking.premium ? 'PREMIUM' : 'STANDARD', quantity: booking.quantity, payment_method: booking.paymentMethod,
      },
    }, RESUME_PATH);
    step.value = 'done';
    emit('booked');
  } catch (err) {
    error.value = err.message;
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
        <span :class="{ current: step === 'payment' }">02 모의 결제</span><span>──</span><span>03 완료</span>
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
      <button class="primary" type="button" @click="goPayment">{{ auth.profile ? '모의 결제로 이동 →' : '로그인 후 모의 결제로 이동 →' }}</button>
    </template>

    <!-- 02 모의 결제 -->
    <template v-else-if="step === 'payment'">
      <div class="summary-box">
        <div class="summary-line"><span>예매자 / MBTI</span><span>{{ auth.profile?.name }} / {{ auth.profile?.mbti }}</span></div>
        <div class="summary-line"><span>관람 일시</span><span>{{ booking.date }} {{ booking.slot }}</span></div>
        <div class="summary-line"><span>좌석 / 수량</span><span>{{ booking.premium ? '프리미엄석' : '일반석' }} / {{ booking.quantity }}매</span></div>
        <div class="summary-line total"><span>총 결제 금액</span><b>{{ won(total) }}</b></div>
      </div>
      <p class="field-title">결제 방법</p>
      <div class="payment-options">
        <button
          v-for="m in PAYMENT_METHODS" :key="m" type="button" class="payment-option"
          :class="{ selected: booking.paymentMethod === m }" :aria-pressed="String(booking.paymentMethod === m)" @click="booking.paymentMethod = m"
        >{{ m }}</button>
      </div>
      <div class="demo-note">실제 결제가 발생하지 않는 모의 결제입니다.<br>카드번호·계좌번호를 입력하지 마세요. 완료 시 예매 내역이 티킷 서버에 저장됩니다.</div>
      <form @submit.prevent="pay">
        <label class="check-label"><input v-model="agreed" type="checkbox" required @change="error = ''"><span>공연·날짜·회차·금액을 확인했으며 모의 예매에 동의합니다.</span></label>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="primary" type="submit" :disabled="busy">{{ busy ? '결제 처리 중…' : `${won(total)} 모의 결제하기` }}</button>
      </form>
      <button class="secondary" type="button" @click="step = 'select'">← 날짜·회차 다시 선택</button>
    </template>

    <!-- 03 완료 -->
    <template v-else>
      <div class="success">
        <div class="success-icon">✓</div>
        <h3>새로운 설렘이 기다리고 있어요!</h3>
        <p>{{ order.performance_title }}<br>{{ order.performance_date }} {{ order.session_time }} · {{ order.quantity }}매<br>모의 결제 금액 {{ won(order.amount) }}</p>
        <span class="tag">실제 청구 금액 0원</span>
        <p>예매 내역이 저장되었습니다.</p>
      </div>
      <button class="primary" type="button" @click="emit('view-orders')">예매 내역 확인하기</button>
      <button class="secondary" type="button" @click="emit('close')">다른 공연 둘러보기</button>
    </template>
  </BaseModal>
</template>
