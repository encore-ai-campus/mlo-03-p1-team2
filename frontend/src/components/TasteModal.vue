<script setup>
import { computed } from 'vue';
import BaseModal from './BaseModal.vue';
import { useAuthStore } from '@/stores/auth';

// MBTI 취향 찾기 (E/I에 따른 탐색 예시)
const emit = defineEmits(['close', 'choose']);
const auth = useAuthStore();

const COPY = {
  '콘서트': '음악과 함성 속에서 만나는 새로운 에너지.',
  '스포츠': '함께 응원하고 짜릿한 순간을 나눠요.',
  '전시': '나만의 속도로 작품과 이야기를 만나보세요.',
  '클래식': '선율에 집중하며 깊은 여운을 느껴보세요.',
};
const extrovert = computed(() => auth.profile?.mbti.includes('E'));
const intro = computed(() => (extrovert.value ? '함께 열광하는 라이브의 에너지' : '마음에 오래 남는 나만의 감상'));
const picks = computed(() => (extrovert.value ? ['콘서트', '스포츠'] : ['전시', '클래식']));
</script>

<template>
  <BaseModal title="나를 닮은 취향의 발견" @close="emit('close')">
    <span class="tag">{{ auth.profile?.mbti }} · {{ auth.profile?.name }}님의 취향 탐색</span>
    <h3>{{ intro }}</h3>
    <p class="modal-intro">새로운 공연 취향을 발견해 보세요. MBTI만으로 취향이 정해지지는 않아요. 다양한 장르를 자유롭게 탐색해 주세요.</p>
    <div class="taste-cards">
      <div v-for="c in picks" :key="c" class="taste-card">
        <b>{{ c }}</b><p>{{ COPY[c] }}</p>
        <button class="text-link" type="button" @click="emit('choose', c)">{{ c }} 둘러보기 ↗</button>
      </div>
    </div>
    <div class="demo-note">현재 추천은 MBTI의 E/I에 따른 탐색 예시입니다. 실제 사용자별 선호 통계가 아닙니다.</div>
  </BaseModal>
</template>
