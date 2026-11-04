<script setup>
import { reactive, ref } from 'vue'
import { api } from '../api'
const props = defineProps({ mode: String })
const emit = defineEmits(['authenticated', 'switch'])
const mbtis = ['INTJ','INTP','ENTJ','ENTP','INFJ','INFP','ENFJ','ENFP','ISTJ','ISFJ','ESTJ','ESFJ','ISTP','ISFP','ESTP','ESFP']
const form = reactive({ name: '', email: '', password: '', passwordConfirm: '', mbti: '', consent: false })
const visible = reactive({ password: false, passwordConfirm: false })
const busy = ref(false)
const error = ref('')
async function submit() {
  if (busy.value) return
  error.value = ''
  if (props.mode === 'signup' && !form.name.trim()) { error.value = '닉네임을 입력해 주세요.'; return }
  if (props.mode === 'signup' && form.password !== form.passwordConfirm) { error.value = '비밀번호가 일치하지 않습니다.'; return }
  busy.value = true
  try {
    const body = props.mode === 'signup'
      ? { name: form.name.trim(), email: form.email.trim().toLowerCase(), password: form.password, mbti: form.mbti, consent: form.consent }
      : { email: form.email.trim().toLowerCase(), password: form.password }
    emit('authenticated', await api(`/auth/${props.mode}`, { method: 'POST', body }))
  } catch (e) { error.value = e.message }
  finally { busy.value = false }
}
</script>

<template>
  <p class="modal-intro">{{ mode === 'signup' ? '설레는 순간을 함께 찾아요.' : '가입한 이메일과 비밀번호로 로그인해 주세요.' }}</p>
  <form :id="mode === 'signup' ? 'signupForm' : 'loginForm'" @submit.prevent="submit">
    <label v-if="mode === 'signup'" class="form-field">닉네임 <span class="required">*</span><input v-model="form.name" name="nickname" required maxlength="20" autocomplete="nickname" placeholder="티킷에서 사용할 이름"></label>
    <label class="form-field">이메일<input v-model="form.email" name="email" type="email" required maxlength="100" :autocomplete="mode === 'signup' ? 'email' : 'username'" placeholder="hello@example.com"></label>
    <label class="form-field">비밀번호<span class="password-control"><input v-model="form.password" name="password" :type="visible.password ? 'text' : 'password'" required :minlength="mode === 'signup' ? 8 : undefined" maxlength="128" :autocomplete="mode === 'signup' ? 'new-password' : 'current-password'" placeholder="비밀번호 입력"><button type="button" :aria-label="visible.password ? '비밀번호 숨기기' : '비밀번호 표시'" :aria-pressed="visible.password" @click="visible.password = !visible.password">{{ visible.password ? '숨기기' : '보기' }}</button></span></label>
    <template v-if="mode === 'signup'">
      <label class="form-field">비밀번호 확인<span class="password-control"><input v-model="form.passwordConfirm" name="passwordConfirm" :type="visible.passwordConfirm ? 'text' : 'password'" required minlength="8" maxlength="128" autocomplete="new-password" placeholder="비밀번호를 다시 입력해 주세요"><button type="button" :aria-label="visible.passwordConfirm ? '비밀번호 확인 숨기기' : '비밀번호 확인 표시'" :aria-pressed="visible.passwordConfirm" @click="visible.passwordConfirm = !visible.passwordConfirm">{{ visible.passwordConfirm ? '숨기기' : '보기' }}</button></span></label>
      <p class="field-title">나의 MBTI <span class="required">* 필수</span></p>
      <div class="mbti-options"><label v-for="mbti in mbtis" :key="mbti" class="mbti-option"><input v-model="form.mbti" type="radio" name="mbti" :value="mbti" required><span>{{ mbti }}</span></label></div>
      <label class="check-label"><input v-model="form.consent" type="checkbox" name="consent" required><span>[필수] MBTI·공연 조회·예매 내역을 공연 취향 분석 목적으로 수집하는 데 동의합니다.</span></label>
      <div class="notice">가입 후 나의 공연 예매와 결제 내역을 한곳에서 확인하세요.</div>
    </template>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <button class="primary" type="submit" :disabled="busy">{{ busy ? (mode === 'signup' ? '가입 중…' : '로그인 중…') : (mode === 'signup' ? '동의하고 시작하기' : '로그인') }}</button>
    <button :id="mode === 'signup' ? 'signupToLogin' : 'loginToSignup'" class="secondary" type="button" :disabled="busy" @click="emit('switch', mode === 'signup' ? 'login' : 'signup')">{{ mode === 'signup' ? '이미 계정이 있나요? 로그인' : '처음이신가요? 회원가입' }}</button>
  </form>
</template>
