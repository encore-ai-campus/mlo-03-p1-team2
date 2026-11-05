<script setup>
import PosterArt from './PosterArt.vue';
import { won } from '@/utils';

defineProps({
  show: { type: Object, required: true },
  saved: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
});
const emit = defineEmits(['open', 'favorite']);
</script>

<template>
  <article class="show-card">
    <button class="poster-button" type="button" :aria-label="`${show.title} 상세 및 예매`" @click="emit('open', show.id)">
      <PosterArt :show="show" />
    </button>
    <button
      class="favorite" :class="{ saved }" type="button" :disabled="busy" :aria-label="`${show.title} ${saved ? '찜 해제' : '찜하기'}`" :aria-pressed="String(saved)"
      @click="emit('favorite', show.id)"
    >{{ saved ? '♥' : '♡' }}</button>
    <div class="show-info">
      <div class="tags"><span class="tag">{{ show.tag }}</span><span class="tag neutral">{{ show.category }}</span></div>
      <button class="show-title" type="button" @click="emit('open', show.id)">{{ show.title }}</button>
      <p>{{ show.venue }}</p>
      <p>{{ show.date_label }}</p>
      <div class="price-line">{{ won(show.price) }} <small>부터</small></div>
    </div>
  </article>
</template>
