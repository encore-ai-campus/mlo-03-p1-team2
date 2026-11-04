<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import ProfileForm from '@/components/mypage/ProfileForm.vue';
import PasswordForm from '@/components/mypage/PasswordForm.vue';
import ComingSoon from '@/components/mypage/ComingSoon.vue';

// 마이페이지: 왼쪽 메뉴 + 오른쪽 내용. 주소(/mypage/password 등)로 메뉴를 전환합니다.
// 새 기능을 붙일 때는 MENU에서 해당 항목의 soon을 지우고 component에 화면 컴포넌트를 연결하면 됩니다.
const MENU = [
  { group: '나의 계정', items: [
    { id: 'profile', label: '회원 정보 수정', component: ProfileForm },
    { id: 'password', label: '비밀번호 변경', component: PasswordForm },
  ] },
  { group: '나의 티켓', items: [
    { id: 'orders', label: '예매 내역', soon: '예매한 공연의 관람 일시·좌석·결제 정보를 한눈에 확인하고 관리할 수 있어요.' },
    { id: 'refunds', label: '취소·환불 내역', soon: '예매 취소 신청과 환불 진행 상황을 확인할 수 있어요.' },
    { id: 'favorites', label: '찜한 공연', soon: '하트로 담아 둔 공연을 모아 보고 바로 예매할 수 있어요.' },
  ] },
  { group: '나의 취향', items: [
    { id: 'taste', label: 'MBTI 취향 리포트', soon: '나의 관람 기록과 같은 MBTI 사용자의 취향을 분석해 보여드려요.' },
  ] },
  { group: '설정', items: [
    { id: 'notifications', label: '알림 설정', soon: '티켓 오픈·관람일 알림을 받을 방법을 선택할 수 있어요.' },
    { id: 'withdraw', label: '회원 탈퇴', soon: '계정과 연결된 모든 데이터를 삭제하고 탈퇴할 수 있어요.' },
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
                  >{{ i.label }}<span v-if="i.soon" class="soon-pill">준비 중</span></RouterLink>
                </li>
              </ul>
            </template>
          </nav>
        </aside>
        <section class="mypage-panel" aria-live="polite">
          <ComingSoon v-if="active.soon" :key="active.id" :item="active" />
          <component :is="active.component" v-else :key="active.id" />
        </section>
      </div>
    </div>
  </main>
</template>
