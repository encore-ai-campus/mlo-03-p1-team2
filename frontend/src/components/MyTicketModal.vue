<script setup>
import { computed, ref } from 'vue';
import BaseModal from './BaseModal.vue';
import { useAuthStore } from '@/stores/auth';
import { useAuthedApi } from '@/composables/useAuthedApi';
import { toast } from '@/composables/useToast';
import { won } from '@/utils';

// 마이티킷: 예매 내역·찜한 공연·데이터 내려받기·계정 삭제
const NEXT = '/?open=mytikit';
const props = defineProps({
  orders: { type: Array, required: true },
  liked: { type: Array, default: () => [] },
});
const emit = defineEmits(['close', 'open-show', 'deleted']);

const auth = useAuthStore();
const authed = useAuthedApi();
const confirming = ref(false);
const deleting = ref(false);
const title = computed(() => (confirming.value ? '내 데이터 삭제' : '마이티킷'));

const seat = o => (o.seat_grade === 'PREMIUM' ? '프리미엄석' : '일반석');
const orderNo = o => String(o.id).slice(0, 8).toUpperCase();
const createdAt = o => new Date(o.created_at).toLocaleDateString('ko-KR');

async function exportData() {
  try {
    const payload = await authed('/users/me/export', {}, NEXT);
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a');
    a.href = url; a.download = 'tikit-my-data.json'; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast('데이터를 내려받았어요.');
  } catch (err) { toast(err.message); }
}

async function deleteAccount() {
  deleting.value = true;
  try {
    await authed('/users/me', { method: 'DELETE' }, NEXT);
    auth.logout();
    emit('deleted');
    toast('계정과 연결된 데이터를 삭제했어요.');
  } catch (err) {
    deleting.value = false;
    toast(err.message);
  }
}
</script>

<template>
  <BaseModal :title="title" @close="emit('close')">
    <template v-if="!confirming">
      <p class="modal-intro">{{ auth.profile?.name }}님의 설레는 순간들 <span class="tag">{{ auth.profile?.mbti }}</span></p>
      <p class="field-title">나의 예매 내역 · {{ props.orders.length }}건</p>
      <template v-if="props.orders.length">
        <article v-for="o in props.orders" :key="o.id" class="order-card">
          <span class="order-status">모의 예매 완료 · 실제 결제 없음</span>
          <h3>{{ o.performance_title }}</h3>
          <p>{{ o.performance_date }} {{ o.session_time }} · {{ o.venue }}<br>{{ seat(o) }} {{ o.quantity }}매 · {{ won(o.amount) }}</p>
          <footer><span>예매번호 {{ orderNo(o) }}</span><span>{{ createdAt(o) }}</span></footer>
        </article>
      </template>
      <div v-else class="demo-note">아직 예매한 공연이 없어요. 마음에 드는 공연을 골라 보세요.</div>
      <p class="field-title">찜한 공연 · {{ props.liked.length }}개</p>
      <button v-for="s in props.liked" :key="s.id" class="secondary" type="button" @click="emit('open-show', s.id)">{{ s.title }} ↗</button>
      <button class="primary" type="button" @click="exportData">내 취향·예매 데이터 내려받기 (JSON)</button>
      <button class="secondary" type="button" @click="confirming = true">내 계정·취향·예매 데이터 삭제</button>
    </template>
    <template v-else>
      <p class="modal-intro">계정과 연결된 공연 조회·찜·모의 예매 내역을 서버에서 삭제합니다. 삭제 후 복구할 수 없습니다.</p>
      <button class="primary" type="button" :disabled="deleting" @click="deleteAccount">내 데이터 삭제하기</button>
      <button class="secondary" type="button" @click="confirming = false">마이티킷으로 돌아가기</button>
    </template>
  </BaseModal>
</template>
