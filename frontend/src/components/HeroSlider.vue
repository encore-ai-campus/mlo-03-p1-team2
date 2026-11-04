<script setup>
import { computed, ref } from 'vue';
import { photo } from '@/utils';

// 추천 배너 3장. 공연 정보(제목·장소·이미지)는 서버에서 받은 목록에서 찾습니다.
const props = defineProps({ shows: { type: Array, default: () => [] } });
const emit = defineEmits(['open']);

const slides = [
  { id: 'city', title: ['우리의 밤은', '지금부터 ', '시작이야.'], sticker: ['FEEL', 'YOUR', 'VIBE', 'SEOUL · 2026'], cta: '페스티벌' },
  { id: 'opera', title: ['오래 기다려온', '그 무대, ', '그 전율.'], sticker: ['THE', 'STAGE', 'IS YOURS', 'MUSICAL · 2026'], cta: '뮤지컬' },
  { id: 'color', title: ['일상에 새로운', '색을 ', '더해볼까요.'], sticker: ['COLOR', 'YOUR', 'DAYS', 'EXHIBITION · 2026'], cta: '전시' },
];
const index = ref(0);
const current = computed(() => slides[index.value]);
const show = computed(() => props.shows.find(s => s.id === current.value.id));

function move(delta) { index.value = (index.value + delta + slides.length) % slides.length; }
</script>

<template>
  <section class="hero" aria-label="추천 공연">
    <div class="hero-inner wrap">
      <div class="hero-copy">
        <div class="eyebrow"><span class="live-dot"></span> TIKIT SPECIAL PICK</div>
        <p class="hero-pre">평범한 하루를, 특별한 장면으로.</p>
        <h1>{{ current.title[0] }}<br>{{ current.title[1] }}<em>{{ current.title[2] }}</em></h1>
        <p class="hero-description">
          <template v-if="show">{{ show.title }}<br>{{ show.venue }} · {{ show.date_label }}</template>
          <template v-else>2026 CITY LIGHTS MUSIC FESTIVAL<br>도시의 빛과 음악이 만나는 가장 빛나는 순간</template>
        </p>
        <button class="hero-cta" type="button" @click="emit('open', current.id)">{{ current.cta }} 만나보기 <span>↗</span></button>
        <div class="hero-bottom">
          <span>{{ String(index + 1).padStart(2, '0') }}</span>
          <div class="slide-track"><i :style="{ width: `${((index + 1) / slides.length) * 100}%` }"></i></div>
          <span class="slide-total">0{{ slides.length }}</span>
          <button type="button" aria-label="이전 배너" @click="move(-1)">←</button>
          <button type="button" aria-label="다음 배너" @click="move(1)">→</button>
        </div>
      </div>
      <div class="hero-art">
        <img
          :src="show ? photo(show.image, 1400) : 'https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?auto=format&fit=crop&w=1400&q=85'"
          :alt="show ? `${show.title} 공연 분위기 이미지` : '빛과 음악으로 가득한 야외 페스티벌'"
        >
        <div class="hero-art-shade"></div>
        <div class="hero-sticker">
          {{ current.sticker[0] }}<br>{{ current.sticker[1] }}<br><span>{{ current.sticker[2] }}</span><small>{{ current.sticker[3] }}</small>
        </div>
        <div class="art-caption"><span>음악에 빠지는 순간, 진짜 나를 만나다.</span><span>LIVE LOUD. FEEL MORE. ↗</span></div>
      </div>
    </div>
  </section>
</template>
