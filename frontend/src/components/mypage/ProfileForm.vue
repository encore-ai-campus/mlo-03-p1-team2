<script setup>
import { computed, reactive, ref } from 'vue';
import PanelHead from './PanelHead.vue';
import PasswordField from '@/components/PasswordField.vue';
import { useAuthStore } from '@/stores/auth';
import { useAuthedApi } from '@/composables/useAuthedApi';
import { toast } from '@/composables/useToast';
import { MBTIS, formatDate } from '@/utils';

// 회원 정보 수정: 닉네임·이메일·MBTI. 이메일을 바꿀 때만 현재 비밀번호를 받습니다.
const auth = useAuthStore();
const authed = useAuthedApi();

const form = reactive({ name: '', email: '', mbti: '', currentPassword: '' });
const emailInput = ref(null);
const error = ref('');
const busy = ref(false);

function reset() {
  Object.assign(form, { name: auth.profile.name, email: auth.profile.email, mbti: auth.profile.mbti, currentPassword: '' });
}
reset();

const emailChanged = computed(() => form.email.trim().toLowerCase() !== auth.profile.email);

async function submit() {
  if (busy.value) return;
  const name = form.name.trim();
  const email = form.email.trim().toLowerCase();
  if (!name) { error.value = '닉네임을 입력해 주세요.'; return; }
  if (!email || !emailInput.value.checkValidity()) { error.value = '올바른 이메일 주소를 입력해 주세요.'; return; }

  const body = {};
  if (name !== auth.profile.name) body.name = name;
  if (form.mbti && form.mbti !== auth.profile.mbti) body.mbti = form.mbti;
  if (emailChanged.value) {
    if (!form.currentPassword) { error.value = '이메일을 변경하려면 현재 비밀번호를 입력해 주세요.'; return; }
    body.email = email;
    body.current_password = form.currentPassword;
  }
  if (!Object.keys(body).length) { error.value = '변경된 내용이 없어요.'; return; }

  busy.value = true;
  try {
    auth.profile = await authed('/users/me', { method: 'PATCH', body });
    reset();
    toast('회원 정보를 변경했어요.');
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <PanelHead kicker="ACCOUNT" title="회원 정보 수정" intro="닉네임·이메일·MBTI를 변경할 수 있어요. 이메일을 바꾸면 다음 로그인부터 새 이메일을 사용합니다." />
  <form class="mypage-form" novalidate @submit.prevent="submit" @input="error = ''" @change="error = ''">
    <label class="form-field"><span>닉네임 <span class="required">*</span></span><input v-model="form.name" name="name" required maxlength="20" autocomplete="nickname"></label>
    <label class="form-field"><span>이메일 <span class="required">*</span></span><input ref="emailInput" v-model="form.email" name="email" type="email" required maxlength="100" autocomplete="email"></label>
    <PasswordField
      v-if="emailChanged" v-model="form.currentPassword" label="현재 비밀번호" name="currentPassword"
      placeholder="이메일 변경을 위해 현재 비밀번호를 입력해 주세요"
    />
    <p id="mbtiTitle" class="field-title">나의 MBTI <span class="required">*</span></p>
    <div class="mbti-options" role="radiogroup" aria-labelledby="mbtiTitle">
      <label v-for="m in MBTIS" :key="m" class="mbti-option"><input v-model="form.mbti" type="radio" name="mbti" :value="m"><span>{{ m }}</span></label>
    </div>
    <dl class="mypage-meta">
      <div><dt>가입일</dt><dd>{{ formatDate(auth.profile.created_at) }}</dd></div>
      <div><dt>정보 수집 동의</dt><dd>{{ auth.profile.consent ? `동의함 (${formatDate(auth.profile.consented_at)})` : '미동의' }}</dd></div>
    </dl>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <button class="primary" type="submit" :disabled="busy">{{ busy ? '저장 중…' : '변경 내용 저장' }}</button>
  </form>
</template>
