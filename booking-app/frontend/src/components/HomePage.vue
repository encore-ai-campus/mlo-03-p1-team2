<script setup>
import { computed, ref } from 'vue'
import ShowPoster from './ShowPoster.vue'
import { photo, won } from '../utils'
const props = defineProps({ shows: Array, favorites: Array, category: String, search: String, expanded: Boolean })
const emit = defineEmits(['category', 'show', 'favorite', 'taste', 'expand'])
const categories = ['전체','콘서트','뮤지컬','스포츠','전시','클래식','연극']
const sort = ref('popular')
const rank = ref('all')
const heroIndex = ref(0)
const heroIds = ['city','opera','color']
const hero = computed(() => props.shows.find(show => show.id === heroIds[heroIndex.value]))
const heroCopy = [
  ['우리의 밤은', '지금부터 ', '시작이야.', 'FEEL', 'YOUR', 'VIBE', 'SEOUL', '페스티벌'],
  ['오래 기다려온', '그 무대, ', '그 전율.', 'THE', 'STAGE', 'IS YOURS', 'MUSICAL', '뮤지컬'],
  ['일상에 새로운', '색을 ', '더해볼까요.', 'COLOR', 'YOUR', 'DAYS', 'EXHIBITION', '전시'],
]
const copy = computed(() => heroCopy[heroIndex.value])
const filtered = computed(() => {
  const list = props.shows.filter(show => (props.category === '전체' || show.category === props.category)
    && `${show.title} ${show.venue} ${show.category}`.toLowerCase().includes(props.search.toLowerCase()))
  if (sort.value === 'date') list.sort((a, b) => a.start.localeCompare(b.start))
  if (sort.value === 'price') list.sort((a, b) => a.price - b.price)
  return list
})
const visible = computed(() => props.expanded ? filtered.value : filtered.value.slice(0, 4))
const ranking = computed(() => props.shows.filter(show => rank.value === 'all' || show.category === rank.value).slice(0, 3))
const title = computed(() => props.search ? `“${props.search}” 검색 결과` : props.category === '전체' ? '지금, 가장 설레는 공연' : `${props.category}, 나의 다음 설렘`)
function slide(delta) { heroIndex.value = (heroIndex.value + delta + heroIds.length) % heroIds.length }
</script>

<template>
  <main id="homePage">
    <section v-if="hero" class="hero" aria-label="추천 공연"><div class="hero-inner wrap"><div class="hero-copy"><div class="eyebrow"><span class="live-dot"></span> TIKIT SPECIAL PICK</div><p class="hero-pre">평범한 하루를, 특별한 장면으로.</p><h1 id="heroTitle">{{ copy[0] }}<br>{{ copy[1] }}<em>{{ copy[2] }}</em></h1><p id="heroDescription" class="hero-description">{{ hero.title }}<br>{{ hero.venue }} · {{ hero.date }}</p><button id="heroBook" class="hero-cta" @click="emit('show', hero.id)">{{ copy[7] }} 만나보기 <span>↗</span></button><div class="hero-bottom"><span id="heroIndex">{{ String(heroIndex + 1).padStart(2, '0') }}</span><div class="slide-track"><i id="slideProgress" :style="{ width: `${(heroIndex + 1) / 3 * 100}%` }"></i></div><span class="slide-total">03</span><button id="prevSlide" aria-label="이전 배너" @click="slide(-1)">←</button><button id="nextSlide" aria-label="다음 배너" @click="slide(1)">→</button></div></div><div class="hero-art"><img id="heroImage" :src="photo(hero.image, 1400)" :alt="`${hero.title} 공연 분위기 이미지`"><div class="hero-art-shade"></div><div class="hero-sticker">{{ copy[3] }}<br>{{ copy[4] }}<br><span>{{ copy[5] }}</span><small>{{ copy[6] }} · 2026</small></div><div class="art-caption"><span>음악에 빠지는 순간, 진짜 나를 만나다.</span><span>LIVE LOUD. FEEL MORE. ↗</span></div></div></div></section>
    <section id="performances" class="section wrap"><div class="section-head"><div><div class="section-kicker">YOUR NEXT MOMENT</div><h2 id="listTitle">{{ title }} <span>✦</span></h2></div></div><div class="filter-row"><div id="categoryChips" class="chips"><button v-for="c in categories" :key="c" :data-category="c" :class="['chip', { active: c === category }]" :aria-pressed="c === category" @click="emit('category', c)">{{ c }}</button></div><select id="sortSelect" v-model="sort" aria-label="공연 정렬"><option value="popular">인기순</option><option value="date">공연일순</option><option value="price">낮은 가격순</option></select></div>
      <div id="performanceGrid" class="performance-grid"><article v-for="show in visible" :key="show.id" class="show-card"><button class="poster-button" :data-show="show.id" :aria-label="`${show.title} 상세 및 예매`" @click="emit('show', show.id)"><ShowPoster :show="show" /></button><button :class="['favorite', { saved: favorites.includes(show.id) }]" :data-favorite="show.id" :aria-label="`${show.title} 찜하기`" :aria-pressed="favorites.includes(show.id)" @click="emit('favorite', show.id)">{{ favorites.includes(show.id) ? '♥' : '♡' }}</button><div class="show-info"><div class="tags"><span class="tag">{{ show.tag }}</span><span class="tag neutral">{{ show.category }}</span></div><button class="show-title" :data-show="show.id" @click="emit('show', show.id)">{{ show.title }}</button><p>{{ show.venue }}</p><p>{{ show.date }}</p><div class="price-line">{{ won(show.price) }} <small>부터</small></div></div></article></div>
      <div v-if="!filtered.length" id="emptyState" class="empty">검색 결과가 없어요.<br><small>다른 공연명이나 장소로 검색해 보세요.</small></div><button v-if="filtered.length > 4" id="moreButton" class="more-button" @click="emit('expand')">{{ expanded ? '간략히 보기' : '더 많은 설렘 만나보기' }} <span>{{ expanded ? '−' : '＋' }}</span></button>
    </section>
    <section class="mbti-banner wrap"><div class="mbti-symbols"><span>ENFP</span><span>✳</span><span>INTJ</span><span>✦</span></div><div class="mbti-copy"><span class="section-kicker">A LITTLE MORE YOU</span><h2>같은 MBTI는, 어떤 공연을 좋아할까?</h2><p>나를 닮은 사람들의 취향에서 새로운 인생 공연을 발견해 보세요.</p></div><button id="mbtiBannerButton" @click="emit('taste')">내 취향 찾으러 가기 <span>↗</span></button></section>
    <section class="section ranking-section wrap"><div class="section-head"><div><div class="section-kicker">TRENDING RIGHT NOW</div><h2>요즘 모두의 관심사 <span class="tiny-pill">HOT</span></h2></div><div class="rank-tabs"><button v-for="c in ['all', '콘서트', '뮤지컬']" :key="c" :class="{ active: rank === c }" :data-rank="c" :aria-pressed="rank === c" @click="rank = c">{{ c === 'all' ? '전체' : c }}</button></div></div><div id="rankingGrid" class="ranking-grid"><button v-for="(show, i) in ranking" :key="show.id" class="rank-card" :data-show="show.id" @click="emit('show', show.id)"><span class="rank-number">{{ i + 1 }}</span><img :src="photo(show.image, 200)" alt="" loading="lazy"><div class="rank-copy"><small>{{ show.category }}</small><b>{{ show.title }}</b><p>{{ show.venue }}</p></div></button></div></section>
    <section class="service-strip wrap"><div><b>좋아하는 순간을 놓치지 않도록.</b><p>당신의 다음 설렘도 티킷과 함께하세요.</p></div><div><span>✧ 취향을 발견하고</span><span>♡ 좋아함을 모으고</span><span>↗ 새로운 순간으로</span></div></section>
  </main>
</template>
