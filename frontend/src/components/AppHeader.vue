<script setup>
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { toast } from '@/composables/useToast';
import { CATEGORIES, loginRoute, safeNext, signupRoute } from '@/utils';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const isHome = computed(() => route.name === 'home');
const activeCategory = computed(() => {
  if (!isHome.value) return '';
  const c = route.query.category;
  return CATEGORIES.includes(c) ? c : '전체';
});

// 카테고리 메뉴는 메인 주소(/?category=…)로 이동하는 링크라서 어느 화면에서 눌러도 동작합니다.
const categoryLink = c => (c === '전체' ? { path: '/' } : { path: '/', query: { category: c } });

// 로그인·회원가입 화면에 있을 때는 next 값을 그대로 넘겨 원래 화면으로 돌아가게 합니다.
const next = computed(() => (route.meta.guestOnly ? safeNext(route.query.next) : route.fullPath));

/* ---------- 검색 ---------- */
const keyword = ref('');
watch(() => route.query.q, q => { keyword.value = isHome.value && typeof q === 'string' ? q : ''; }, { immediate: true });

function submitSearch() {
  const q = keyword.value.trim().slice(0, 100);
  router.push({ path: '/', query: q ? { q } : {} });
}
// 검색 중에 입력칸을 비우면 전체 목록으로 돌아갑니다.
function onSearchInput() {
  if (!keyword.value && isHome.value && route.query.q) {
    const { q, ...rest } = route.query;
    router.replace({ path: '/', query: rest });
  }
}

/* ---------- 계정 ---------- */
function logout() {
  auth.logout();
  if (route.meta.requiresAuth) router.push('/');
  toast('로그아웃했어요.');
}
</script>

<template>
  <header>
    <div class="header-main wrap">
      <RouterLink to="/" class="logo" aria-label="티킷 홈">ti<span>k</span>it<span class="logo-dot">.</span></RouterLink>
      <form class="search" role="search" @submit.prevent="submitSearch">
        <input v-model="keyword" name="q" type="search" maxlength="100" placeholder="어떤 설렘을 찾고 있나요?" aria-label="공연 검색" @input="onSearchInput">
        <button aria-label="검색" type="submit"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4.5 4.5" /></svg></button>
      </form>
      <div class="account">
        <template v-if="auth.profile">
          <RouterLink to="/mypage" class="account-name">{{ auth.profile.name }}님</RouterLink><span></span>
          <RouterLink to="/mypage">마이페이지</RouterLink><span></span>
          <button type="button" @click="logout">로그아웃</button>
        </template>
        <template v-else>
          <RouterLink :to="loginRoute(next)">로그인</RouterLink><span></span>
          <RouterLink :to="signupRoute(next)">회원가입</RouterLink>
        </template>
        <RouterLink :to="{ path: '/', query: { ...(isHome ? route.query : {}), open: 'mytikit' } }" class="my-ticket">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v5a2 2 0 0 0 0 4v5H4v-5a2 2 0 0 0 0-4Z" /><path d="M15 5v3m0 3v2m0 3v3" /></svg> 마이티킷
        </RouterLink>
      </div>
    </div>
    <nav class="wrap nav" aria-label="공연 카테고리">
      <div class="genre-nav">
        <RouterLink
          v-for="c in CATEGORIES" :key="c" :to="categoryLink(c)"
          :class="{ active: c === activeCategory }" :aria-current="c === activeCategory ? 'page' : undefined"
          active-class="" exact-active-class=""
        >{{ c === '전체' ? '홈' : c }}</RouterLink>
      </div>
      <RouterLink v-if="isHome" class="taste-nav" :to="{ path: '/', query: { ...route.query, open: 'taste' } }">
        <span>✦</span> MBTI 취향 찾기 <span class="new">NEW</span>
      </RouterLink>
    </nav>
  </header>
</template>
