<script setup>
import { computed, ref } from 'vue'
import ShowPoster from './ShowPoster.vue'
import { availableDates, won, paymentLabels } from '../utils'
import { api } from '../api'
const props = defineProps({ show: Object, booking: Object, profile: Object, confirmation: Boolean })
const emit = defineEmits(['login', 'title', 'tickets', 'pay', 'close', 'toast'])
const step = ref(props.confirmation ? 'confirm' : 'select')
const busy = ref(false)
const error = ref('')
const order = ref(null)
const total = computed(() => (props.show.price + props.booking.premium) * props.booking.quantity)
const dates = computed(() => availableDates(props.show))
const dayLabel = date => ['일','월','화','수','목','금','토'][new Date(date + 'T12:00:00').getDay()]
function confirm() {
  if (!props.profile) { emit('login'); return }
  step.value = 'confirm'
  emit('title', '예매 확인')
}
function back() {
  props.booking.requestKey = crypto.randomUUID()
  step.value = 'select'
  emit('title', '공연 예매')
}
async function submit() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    const b = props.booking
    order.value = await api('/reservations', { method: 'POST', body: {
      performanceId: props.show.id, performanceDate: b.date, sessionTime: b.slot,
      seatGrade: b.premium ? 'PREMIUM' : 'STANDARD', quantity: b.quantity, requestKey: b.requestKey,
    } })
    step.value = 'success'
    emit('title', '예매 완료')
    emit('toast', '예매가 완료되었습니다. 마이티킷에서 확인하세요.')
  } catch (e) { error.value = e.message }
  finally { busy.value = false }
}
</script>

<template>
  <template v-if="step !== 'success'">
    <div v-if="step === 'select'" class="booking-steps"><span class="current">01 날짜 · 회차</span><span>──</span><span>02 예매 확인</span><span>──</span><span>03 완료</span></div>
    <div class="detail-top"><ShowPoster :show="show" /><div><span class="tag">{{ show.category }}</span><h3>{{ show.title }}</h3><p>{{ show.venue }}</p><p>{{ show.date }}</p><p>만 7세 이상 · 약 120분</p></div></div>
    <template v-if="step === 'select'">
      <p class="field-title">관람 날짜 선택</p>
      <div class="date-options"><button v-for="date in dates" :key="date" :data-date="date" :class="['date-option', { selected: booking.date === date }]" :aria-pressed="booking.date === date" @click="booking.date = date"><small>{{ dayLabel(date) }}</small>{{ Number(date.slice(5, 7)) }}.{{ date.slice(8) }}</button></div>
      <p class="field-title">회차 선택</p>
      <div class="slot-options"><button v-for="slot in show.slots" :key="slot" :data-slot="slot" :class="['slot-option', { selected: booking.slot === slot }]" :aria-pressed="booking.slot === slot" @click="booking.slot = slot">{{ slot }}</button></div>
      <div class="seat-quantity"><label><p class="field-title">좌석 등급</p><select id="seatSelect" v-model.number="booking.premium"><option :value="0">일반석 · {{ won(show.price) }}</option><option :value="30000">프리미엄석 · {{ won(show.price + 30000) }}</option></select></label><label><p class="field-title">예매 수량</p><select id="quantitySelect" v-model.number="booking.quantity"><option v-for="n in 4" :key="n" :value="n">{{ n }}매</option></select></label></div>
      <div class="summary-box"><div class="summary-line"><span>티켓 금액</span><span id="ticketSubtotal">{{ won(total) }}</span></div><div class="summary-line"><span>예매 수수료</span><span>0원</span></div><div class="summary-line total"><span>총 결제 금액</span><b id="bookingTotal">{{ won(total) }}</b></div></div>
      <button id="confirmBooking" class="primary" @click="confirm">{{ profile ? '예매하기' : '로그인 후 예매하기 →' }}</button>
    </template>
    <template v-else>
      <div class="summary-box"><div class="summary-line"><span>예매자</span><span>{{ profile.name }}</span></div><div class="summary-line"><span>관람 일시</span><span>{{ booking.date }} {{ booking.slot }}</span></div><div class="summary-line"><span>좌석 / 수량</span><span>{{ booking.premium ? '프리미엄석' : '일반석' }} / {{ booking.quantity }}매</span></div><div class="summary-line total"><span>결제 예정 금액</span><b>{{ won(total) }}</b></div></div>
      <p class="modal-intro">예매 내용을 확인해 주세요. 예매 후 결제를 진행할 수 있어요.</p>
      <form id="bookingForm" @submit.prevent="submit"><label class="check-label"><input type="checkbox" required><span>공연·날짜·회차·금액을 확인했으며 예매에 동의합니다.</span></label><p v-if="error" class="form-error" role="alert">{{ error }}</p><button class="primary" type="submit" :disabled="busy">{{ busy ? '예매 중…' : `예매하기 · ${won(total)}` }}</button></form>
      <button id="backToDates" class="secondary" :disabled="busy" @click="back">← 날짜·회차 다시 선택</button>
    </template>
  </template>
  <template v-else>
    <div class="success"><div class="success-icon">✓</div><h3>설레는 순간을 예약했어요!</h3><p>{{ order.performanceTitle }}<br>{{ order.performanceDate }} {{ order.sessionTime }} · {{ order.quantity }}매</p><span :class="['order-status', `status-${order.paymentStatus.toLowerCase()}`]">{{ paymentLabels[order.paymentStatus] }}</span><p>결제 예정 금액 {{ won(order.amount) }}<br>마이티킷에서 예매 내역을 확인할 수 있어요.</p></div>
    <button id="payNow" class="primary" :disabled="busy" @click="busy = true; emit('pay', order.id, () => busy = false)">결제하기</button>
    <button id="viewOrders" class="secondary" @click="emit('tickets')">예매 내역 확인하기</button>
    <button class="secondary" @click="emit('close')">다른 공연 둘러보기</button>
  </template>
</template>
