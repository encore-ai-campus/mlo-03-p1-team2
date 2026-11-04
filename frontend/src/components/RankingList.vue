<script setup>
import { computed, ref } from 'vue';
import { photo } from '@/utils';

const props = defineProps({ ranking: { type: Array, default: () => [] } });
const emit = defineEmits(['open']);

const tabs = [{ id: 'all', label: '전체' }, { id: '콘서트', label: '콘서트' }, { id: '뮤지컬', label: '뮤지컬' }];
const tab = ref('all');
const top3 = computed(() => props.ranking.filter(s => tab.value === 'all' || s.category === tab.value).slice(0, 3));
</script>

<template>
  <section class="section ranking-section wrap">
    <div class="section-head">
      <div><div class="section-kicker">TRENDING RIGHT NOW</div><h2>요즘 모두의 관심사 <span class="tiny-pill">HOT</span></h2></div>
      <div class="rank-tabs">
        <button v-for="t in tabs" :key="t.id" type="button" :class="{ active: tab === t.id }" @click="tab = t.id">{{ t.label }}</button>
      </div>
    </div>
    <div class="ranking-grid">
      <button v-for="(s, i) in top3" :key="s.id" class="rank-card" type="button" @click="emit('open', s.id)">
        <span class="rank-number">{{ i + 1 }}</span>
        <img :src="photo(s.image, 200)" alt="" loading="lazy">
        <div class="rank-copy"><small>{{ s.category }}</small><b>{{ s.title }}</b><p>{{ s.venue }}</p></div>
      </button>
    </div>
  </section>
</template>
