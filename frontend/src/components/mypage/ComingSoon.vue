<script setup>
import PanelHead from './PanelHead.vue';

// 아직 개발 전인 메뉴의 안내 화면
defineProps({ item: { type: Object, required: true } });
</script>

<template>
  <PanelHead kicker="COMING SOON" :title="item.label" />
  <div class="soon-box">
    <div class="soon-icon">✦</div>
    <b>곧 만나볼 수 있어요</b>
    <p>{{ item.soon }}</p>
    <RouterLink class="secondary soon-link" to="/">공연 둘러보기 ↗</RouterLink>
  </div>
</template>
