<script setup>
import { reactive, ref } from 'vue';
import PanelHead from './PanelHead.vue';
import PasswordField from '@/components/PasswordField.vue';
import { useAuthedApi } from '@/composables/useAuthedApi';
import { toast } from '@/composables/useToast';

// 비밀번호 변경: 현재 비밀번호를 확인한 뒤 새 비밀번호로 바꿉니다.
const authed = useAuthedApi();
const empty = () => ({ current: '', next: '', confirm: '' });
const form = reactive(empty());
const error = ref('');
const busy = ref(false);

function clientError() {
  if (!form.current) return '현재 비밀번호를 입력해 주세요.';
  if (form.next.length < 8 || form.next.length > 128) return '새 비밀번호는 8~128자로 입력해 주세요.';
  if (form.next !== form.confirm) return '새 비밀번호가 일치하지 않습니다.';
  if (form.next === form.current) return '현재 비밀번호와 다른 비밀번호를 입력해 주세요.';
  return null;
}

async function submit() {
  if (busy.value) return;
  const message = clientError();
  if (message) { error.value = message; return; }

  busy.value = true;
  try {
    await authed('/users/me/password', {
      method: 'PUT',
      body: { current_password: form.current, new_password: form.next, new_password_confirm: form.confirm },
    });
    Object.assign(form, empty());
    toast('비밀번호를 변경했어요. 다음 로그인부터 새 비밀번호를 사용해 주세요.');
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <PanelHead kicker="SECURITY" title="비밀번호 변경" intro="안전을 위해 현재 비밀번호를 확인한 뒤 변경합니다." />
  <form class="mypage-form" novalidate @submit.prevent="submit" @input="error = ''">
    <PasswordField v-model="form.current" label="현재 비밀번호" name="currentPassword" placeholder="현재 비밀번호 입력" />
    <PasswordField v-model="form.next" label="새 비밀번호" name="newPassword" autocomplete="new-password" placeholder="8~128자 입력" />
    <PasswordField v-model="form.confirm" label="새 비밀번호 확인" name="newPasswordConfirm" autocomplete="new-password" placeholder="새 비밀번호를 다시 입력해 주세요" />
    <div class="demo-note">시연용 서비스입니다. 실제 사용하는 비밀번호는 입력하지 마세요.</div>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <button class="primary" type="submit" :disabled="busy">{{ busy ? '변경 중…' : '비밀번호 변경' }}</button>
  </form>
</template>
