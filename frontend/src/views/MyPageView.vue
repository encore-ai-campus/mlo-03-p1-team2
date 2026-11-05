<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import ProfileForm from '@/components/mypage/ProfileForm.vue';
import PasswordForm from '@/components/mypage/PasswordForm.vue';
import OrdersPanel from '@/components/mypage/OrdersPanel.vue';
import FavoritesPanel from '@/components/mypage/FavoritesPanel.vue';
import TasteReportPanel from '@/components/mypage/TasteReportPanel.vue';
import NotificationsPanel from '@/components/mypage/NotificationsPanel.vue';
import WithdrawPanel from '@/components/mypage/WithdrawPanel.vue';

// 마이페이지: 왼쪽 메뉴 + 오른쪽 내용. 주소(/mypage/password 등)로 메뉴를 전환합니다.
// 각 메뉴는 마이페이지 안의 기능 패널을 표시합니다.
const MENU = [
  { group: '나의 계정', items: [
    { id: 'profile', label: '회원 정보 수정', component: ProfileForm },
    { id: 'password', label: '비밀번호 변경', component: PasswordForm },
  ] },
  { group: '나의 티켓', items: [
    { id: 'orders', label: '예매 내역', component: OrdersPanel },
    { id: 'favorites', label: '찜한 공연', component: FavoritesPanel },
  ] },
  { group: '나의 취향', items: [
    { id: 'taste', label: 'MBTI 취향 리포트', component: TasteReportPanel },
  ] },
  { group: '설정', items: [
    { id: 'notifications', label: '알림 설정', component: NotificationsPanel },
    { id: 'withdraw', label: '회원 탈퇴', component: WithdrawPanel },
  ] },
];
const ITEMS = MENU.flatMap(g => g.items);
const DEFAULT_TAB = 'profile';

const route = useRoute();
const auth = useAuthStore();
const active = computed(() => ITEMS.find(i => i.id === route.params.section) || ITEMS.find(i => i.id === DEFAULT_TAB));
</script>

<template>
  <main class="mypage-main">
    <div class="wrap">
      <div class="mypage-head">
        <div class="section-kicker">MY PAGE</div>
        <h1>마이페이지 <span>✦</span></h1>
      </div>

      <div v-if="auth.profile" class="mypage-layout">
        <aside class="mypage-side">
          <div class="mypage-profile">
            <span class="mypage-mbti">{{ auth.profile.mbti }}</span>
            <div><b>{{ auth.profile.name }}님</b><p>{{ auth.profile.email }}</p></div>
          </div>
          <nav class="mypage-menu" aria-label="마이페이지 메뉴">
            <template v-for="g in MENU" :key="g.group">
              <p class="mypage-menu-title">{{ g.group }}</p>
              <ul>
                <li v-for="i in g.items" :key="i.id">
                  <RouterLink
                    :to="`/mypage/${i.id}`" :class="{ active: i.id === active.id }"
                    :aria-current="i.id === active.id ? 'page' : undefined" active-class="" exact-active-class=""
                  >{{ i.label }}</RouterLink>
                </li>
              </ul>
            </template>
          </nav>
        </aside>
        <section class="mypage-panel" aria-live="polite">
          <component :is="active.component" :key="active.id" />
        </section>
      </div>
    </div>
  </main>
</template>
