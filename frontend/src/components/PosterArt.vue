<script setup>
import { photo } from '@/utils';

defineProps({ show: { type: Object, required: true } });
</script>

<template>
  <div class="poster" :class="`poster-${show.style}`">
    <img :src="photo(show.image)" alt="" loading="lazy">
    <span class="poster-label">{{ show.badge }}</span>
    <span class="poster-eyebrow">TIKIT PRESENTS · 2026</span>
    <span class="poster-title">{{ show.english }}</span>
    <span class="poster-sub">{{ show.sub }}</span>
    <span class="poster-date">{{ show.date_label }} · SEOUL</span>
  </div>
</template>
