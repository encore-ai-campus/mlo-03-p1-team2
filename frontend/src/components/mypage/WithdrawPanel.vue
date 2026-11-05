<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import PanelHead from './PanelHead.vue';
import BaseModal from '@/components/BaseModal.vue';
import { useAuthStore } from '@/stores/auth';
import { useAuthedApi } from '@/composables/useAuthedApi';
import { toast } from '@/composables/useToast';

const auth = useAuthStore();
const authed = useAuthedApi();
const router = useRouter();
const agreed = ref(false);
const confirming = ref(false);
const busy = ref(false);
const error = ref('');
const trigger = ref(null);

function close() {
  if (busy.value) return;
  confirming.value = false;
  trigger.value?.focus();
}
async function withdraw() {
  if (busy.value || !agreed.value) return;
  busy.value = true;
  error.value = '';
  try {
    await authed('/users/me', { method: 'DELETE' });
    auth.logout();
    confirming.value = false;
    await router.replace('/');
    toast('회원 탈퇴가 완료되었습니다.');
  } catch (err) { error.value = err.message; }
  finally { busy.value = false; }
}
</script>

<template>
  <PanelHead kicker="ACCOUNT" title="회원 탈퇴" intro="탈퇴하기 전에 아래 내용을 확인해 주세요." />
  <div class="withdraw-notice">
    <h3>{{ auth.profile?.name }}님, 탈퇴하면 계정의 모든 기록이 삭제돼요.</h3>
    <ul><li>회원 정보와 MBTI 정보</li><li>찜한 공연과 공연 조회 기록</li><li>예매·결제 내역과 알림 설정</li></ul>
    <p>삭제한 정보는 복구할 수 없습니다.</p>
  </div>
  <label class="check-label"><input v-model="agreed" type="checkbox"><span>안내 내용을 확인했으며, 계정과 연결된 데이터 삭제에 동의합니다.</span></label>
  <button ref="trigger" type="button" class="primary withdraw-button" :disabled="!agreed || busy" @click="confirming = true">회원 탈퇴</button>
  <BaseModal v-if="confirming" title="회원 탈퇴 확인" @close="close">
    <p class="modal-intro">정말 탈퇴하시겠어요? 계정과 모든 기록이 영구 삭제되며 복구할 수 없습니다.</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <button class="primary withdraw-button" type="button" :disabled="busy" @click="withdraw">{{ busy ? '탈퇴 처리 중…' : '동의하고 탈퇴하기' }}</button>
    <button class="secondary" type="button" :disabled="busy" @click="close">취소</button>
  </BaseModal>
</template>

<style scoped>
.withdraw-notice { border: 1px solid #f0d5db; background: #fff8fa; border-radius: 12px; padding: 22px; }
h3 { font-size: 16px; line-height: 1.7; margin: 0; } ul { padding-left: 20px; font-size: 13px; color: #7e718a; line-height: 2; } p { font-size: 13px; color: #a33744; }
.withdraw-button { background: #a33744; max-width: 300px; } .withdraw-button:disabled { cursor: default; }
</style>
