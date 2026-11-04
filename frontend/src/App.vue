<script setup>
import { onMounted } from 'vue';
import { useRoute } from 'vue-router';
import AppHeader from '@/components/AppHeader.vue';
import AppFooter from '@/components/AppFooter.vue';
import { useAuthStore } from '@/stores/auth';
import { toast, useToast } from '@/composables/useToast';

const route = useRoute();
const auth = useAuthStore();
const { message, visible } = useToast();

// 새로고침해도 저장된 토큰으로 로그인 상태를 복원합니다.
onMounted(() => { auth.restore().catch(err => toast(err.message)); });
</script>

<template>
  <div v-if="route.name === 'home'" class="announcement">나를 닮은 공연을 만나는 새로운 방법 <span>MBTI로 취향 발견하기 ↗</span></div>
  <AppHeader />
  <RouterView />
  <AppFooter v-if="route.meta.footer" />
  <div id="toast" :class="{ show: visible }" role="status" aria-live="polite">{{ message }}</div>
</template>
