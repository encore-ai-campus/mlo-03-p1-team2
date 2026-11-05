<script setup>
import { computed, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import PasswordField from '@/components/PasswordField.vue';
import { useAuthStore } from '@/stores/auth';
import { toast } from '@/composables/useToast';
import { MBTIS, loginRoute, safeNext } from '@/utils';

// 회원가입 화면: 가입이 끝나면 자동 로그인된 상태로 next 주소(없으면 메인)로 이동합니다.
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const next = computed(() => safeNext(route.query.next));

const form = reactive({ nickname: '', email: '', password: '', passwordConfirm: '', mbti: '', consent: false });
const emailInput = ref(null);
const error = ref('');
const busy = ref(false);

// 화면에서 먼저 확인하는 규칙 (서버도 같은 규칙으로 다시 검증합니다)
function clientError() {
  if (!form.nickname.trim()) return '닉네임을 입력해 주세요.';
  if (!form.email.trim() || !emailInput.value.checkValidity()) return '올바른 이메일 주소를 입력해 주세요.';
  if (form.password.length < 8 || form.password.length > 128) return '비밀번호는 8~128자로 입력해 주세요.';
  if (form.password !== form.passwordConfirm) return '비밀번호가 일치하지 않습니다.';
  if (!form.mbti) return 'MBTI를 선택해 주세요.';
  if (!form.consent) return '개인정보 수집에 동의해 주세요.';
  return null;
}

async function submit() {
  if (busy.value) return;
  const message = clientError();
  if (message) { error.value = message; return; }

  busy.value = true;
  try {
    const user = await auth.signup({
      name: form.nickname.trim(),
      email: form.email.trim().toLowerCase(),
      password: form.password,
      passwordConfirm: form.passwordConfirm,
      mbti: form.mbti,
      consent: true,
    });
    toast(`${user.name}님, 가입이 완료됐어요!`);
    router.replace(next.value);
  } catch (err) {
    error.value = err.message;
    busy.value = false;
  }
}
</script>

<template>
  <main class="auth-main">
    <div class="wrap">
      <div class="auth-card">
        <div class="auth-visual">
          <img src="https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?auto=format&fit=crop&w=900&q=80" alt="">
          <div class="hero-sticker">FEEL<br>YOUR<br><span>VIBE</span></div>
          <div class="eyebrow"><span class="live-dot"></span> JOIN TIKIT</div>
          <h1>나의 취향,<br>티킷에서 <em>시작해요.</em></h1>
          <p>MBTI는 공연 취향을 이해하는 데 사용됩니다.<br>가입하고 나를 닮은 설렘을 만나보세요.</p>
        </div>
        <div class="auth-form">
          <div class="section-kicker">SIGN UP</div>
          <h2>회원가입</h2>
          <p class="modal-intro">설레는 순간을 함께 찾아요.</p>
          <form novalidate @submit.prevent="submit" @input="error = ''" @change="error = ''">
            <label class="form-field"><span>닉네임 <span class="required">*</span></span><input v-model="form.nickname" name="nickname" required maxlength="20" autocomplete="nickname" placeholder="티킷에서 사용할 이름" autofocus></label>
            <label class="form-field"><span>이메일 <span class="required">*</span></span><input ref="emailInput" v-model="form.email" name="email" type="email" required maxlength="100" autocomplete="email" placeholder="hello@example.com"></label>
            <PasswordField v-model="form.password" label="비밀번호" name="password" autocomplete="new-password" placeholder="8~128자 입력" />
            <PasswordField v-model="form.passwordConfirm" label="비밀번호 확인" name="passwordConfirm" autocomplete="new-password" placeholder="비밀번호를 다시 입력해 주세요" />
            <p id="mbtiTitle" class="field-title">나의 MBTI <span class="required">* 필수</span></p>
            <div class="mbti-options" role="radiogroup" aria-labelledby="mbtiTitle">
              <label v-for="m in MBTIS" :key="m" class="mbti-option"><input v-model="form.mbti" type="radio" name="mbti" :value="m" required><span>{{ m }}</span></label>
            </div>
            <label class="check-label"><input v-model="form.consent" type="checkbox" name="consent" required><span>[필수] MBTI·공연 조회·모의 예매 내역을 공연 취향 분석 목적으로 수집하는 데 동의합니다. 데이터는 티킷 서버에 보관되며, 마이페이지의 회원 탈퇴에서 삭제할 수 있습니다.</span></label>
            <div class="demo-note">시연용 서비스입니다. 비밀번호는 서버에 원문 대신 해시값으로만 저장됩니다. 실제 사용하는 비밀번호는 입력하지 마세요.</div>
            <p v-if="error" class="form-error" role="alert">{{ error }}</p>
            <button class="primary" type="submit" :disabled="busy">{{ busy ? '가입 중…' : '동의하고 시작하기' }}</button>
          </form>
          <p class="switch-link">이미 계정이 있나요?<RouterLink :to="loginRoute(next)">로그인</RouterLink></p>
        </div>
      </div>
    </div>
  </main>
</template>
