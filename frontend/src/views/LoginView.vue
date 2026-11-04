<script setup>
import { computed, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import PasswordField from '@/components/PasswordField.vue';
import { useAuthStore } from '@/stores/auth';
import { toast } from '@/composables/useToast';
import { safeNext, signupRoute } from '@/utils';

// 로그인 화면: 성공하면 next 주소(없으면 메인)로 이동합니다.
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const next = computed(() => safeNext(route.query.next));

const form = reactive({ email: '', password: '' });
const error = ref('');
const busy = ref(false);

async function submit() {
  if (busy.value) return;
  const email = form.email.trim();
  if (!email || !form.password) { error.value = '이메일과 비밀번호를 입력해 주세요.'; return; }

  busy.value = true;
  try {
    const user = await auth.login(email, form.password);
    toast(`${user.name}님, 반가워요!`);
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
          <img src="https://images.unsplash.com/photo-1503095396549-807759245b35?auto=format&fit=crop&w=900&q=80" alt="">
          <div class="hero-sticker">THE<br>STAGE<br><span>IS YOURS</span></div>
          <div class="eyebrow"><span class="live-dot"></span> WELCOME BACK</div>
          <h1>다시 만나서<br><em>반가워요.</em></h1>
          <p>로그인하고 찜한 공연과 예매 내역을 확인하세요.</p>
        </div>
        <div class="auth-form">
          <div class="section-kicker">LOGIN</div>
          <h2>로그인</h2>
          <p class="modal-intro">가입한 이메일과 비밀번호로 로그인해 주세요.</p>
          <form novalidate @submit.prevent="submit" @input="error = ''">
            <label class="form-field"><span>이메일</span><input v-model="form.email" name="email" type="email" required maxlength="100" autocomplete="username" placeholder="hello@example.com" autofocus></label>
            <PasswordField v-model="form.password" label="비밀번호" name="password" placeholder="비밀번호 입력" :required="false" />
            <p v-if="error" class="form-error" role="alert">{{ error }}</p>
            <button class="primary" type="submit" :disabled="busy">{{ busy ? '로그인 중…' : '로그인' }}</button>
          </form>
          <p class="switch-link">처음이신가요?<RouterLink :to="signupRoute(next)">회원가입</RouterLink></p>
        </div>
      </div>
    </div>
  </main>
</template>
