<script setup>
import PosterArt from './PosterArt.vue';
import { PAYMENT_LABELS, koreanTime, orderNumber, seatLabel, won } from '@/utils';

// 마이티킷의 예매 한 건: 포스터 · 예매 정보 · 결제 금액/상태 · 결제·취소 버튼
defineProps({
  order: { type: Object, required: true },
  show: { type: Object, default: null }, // 공연 정보(포스터). 없으면 포스터를 생략합니다.
  busy: { type: Boolean, default: false },
});
const emit = defineEmits(['open-show', 'complete', 'cancel']);
</script>

<template>
  <article class="ticket-card">
    <button
      v-if="show" type="button" class="ticket-poster"
      :aria-label="`${order.performance_title} 공연 보기`" @click="emit('open-show', order.performance_id)"
    ><PosterArt :show="show" /></button>
    <div class="ticket-details">
      <span class="order-status" :class="`status-${order.payment_status.toLowerCase()}`">{{ PAYMENT_LABELS[order.payment_status] }}</span>
      <h3>{{ order.performance_title }}</h3>
      <p>{{ order.performance_date }} {{ order.session_time }}<br>{{ order.venue }}<br>{{ seatLabel(order.seat_grade) }} · {{ order.quantity }}매</p>
      <footer>예매번호 {{ orderNumber(order.id) }}</footer>
    </div>
    <div class="ticket-payment">
      <div class="ticket-amount"><span>결제 금액</span><b>{{ won(order.amount) }}</b></div>
      <div v-if="order.completed_at" class="payment-completed-at">
        <span>결제 완료 일시</span><time :datetime="order.completed_at">{{ koreanTime(order.completed_at) }}</time>
      </div>
      <div v-if="order.status !== 'CANCELLED'" class="order-actions">
        <button
          v-if="order.payment_status === 'PENDING'" type="button" class="primary" :disabled="busy"
          @click="emit('complete', order)"
        >결제하기</button>
        <button type="button" class="secondary" :disabled="busy" @click="emit('cancel', order)">예매 취소</button>
      </div>
    </div>
  </article>
</template>
