<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import ShowPoster from './ShowPoster.vue'
import { api } from '../api'
import { won, paymentLabels, koreanTime } from '../utils'
const props = defineProps({ profile: Object, shows: Array, favorites: Array, revision: Number, busy: Boolean })
const emit = defineEmits(['login', 'signup', 'show', 'complete', 'cancel'])
const orders = ref([])
const loading = ref(false)
const error = ref('')
const heading = ref(null)
onMounted(() => heading.value?.focus({ preventScroll: true }))
const liked = computed(() => props.shows.filter(show => props.favorites.includes(show.id)))
let request = 0
onBeforeUnmount(() => ++request)
async function load() {
  const id = ++request
  orders.value = []
  error.value = ''
  loading.value = false
  if (!props.profile) return
  loading.value = true
  try {
    const data = await api('/reservations')
    if (id === request) orders.value = data
  } catch (e) { if (id === request) error.value = e.message }
  finally { if (id === request) loading.value = false }
}
watch(() => [props.profile?.id, props.revision], load, { immediate: true })
const findShow = id => props.shows.find(show => show.id === id)
</script>

<template>
  <main id="ticketsPage" aria-labelledby="ticketsHeading">
    <section class="tickets-shell wrap">
      <a href="#" class="tickets-back">← 공연 둘러보기</a>
      <div class="tickets-heading"><div class="section-kicker">MY TIKIT</div><h1 id="ticketsHeading" ref="heading" tabindex="-1">마이티킷</h1><p>예매한 공연과 결제 내역을 한곳에서 확인하세요.</p></div>
      <div id="ticketsContent" aria-live="polite" :aria-busy="loading">
        <div v-if="!profile" class="tickets-empty"><span class="tickets-empty-icon" aria-hidden="true">↗</span><h2>나의 다음 설렘을 확인하세요</h2><p>로그인하면 예매한 공연과 결제 내역을 볼 수 있어요.</p><button id="ticketsLogin" class="primary" @click="emit('login')">로그인하기</button><button id="ticketsSignup" class="secondary" @click="emit('signup')">회원가입</button></div>
        <p v-else-if="loading" class="tickets-loading" role="status">예매 내역을 불러오는 중입니다…</p>
        <div v-else-if="error" class="tickets-empty"><h2>내역을 불러오지 못했어요</h2><p role="alert">{{ error }}</p><button id="retryHistory" class="primary" @click="load">다시 조회하기</button></div>
        <template v-else>
          <div class="tickets-list-heading"><h2>나의 예매 <span>{{ orders.length }}</span></h2><p>{{ profile.name }}님의 설레는 순간들</p></div>
          <div class="tickets-list">
            <article v-for="order in orders" :key="order.id" class="ticket-card">
              <button v-if="findShow(order.performanceId)" class="ticket-poster" :data-show="order.performanceId" :aria-label="`${order.performanceTitle} 공연 보기`" @click="emit('show', order.performanceId)"><ShowPoster :show="findShow(order.performanceId)" /></button>
              <div class="ticket-details"><span :class="['order-status', `status-${order.paymentStatus.toLowerCase()}`]">{{ paymentLabels[order.paymentStatus] }}</span><h3>{{ order.performanceTitle }}</h3><p>{{ order.performanceDate }} {{ order.sessionTime }}<br>{{ order.venue }}<br>{{ order.seatGrade === 'PREMIUM' ? '프리미엄석' : '일반석' }} · {{ order.quantity }}매</p><footer>예매번호 {{ order.id.slice(0, 8).toUpperCase() }}</footer></div>
              <div class="ticket-payment"><div class="ticket-amount"><span>결제 금액</span><b>{{ won(order.amount) }}</b></div><div v-if="order.completedAt" class="payment-completed-at"><span>결제 완료 일시</span><time :datetime="order.completedAt">{{ koreanTime(order.completedAt) }}</time></div><div class="order-actions"><button v-if="order.paymentStatus === 'PENDING'" class="primary" :data-complete="order.id" :disabled="busy" @click="emit('complete', order.id)">결제하기</button><button v-if="order.status !== 'CANCELLED'" class="secondary" :data-cancel-order="order.id" :disabled="busy" @click="emit('cancel', order)">예매 취소</button></div></div>
            </article>
            <div v-if="!orders.length" class="tickets-empty"><span class="tickets-empty-icon" aria-hidden="true">✦</span><h2>아직 예매한 공연이 없어요</h2><p>마음에 드는 공연을 찾아 새로운 설렘을 시작해 보세요.</p><a class="primary" href="#">공연 둘러보기 ↗</a></div>
          </div>
          <section v-if="liked.length" class="ticket-favorites"><h2>찜한 공연 <span>{{ liked.length }}</span></h2><div><button v-for="show in liked" :key="show.id" class="secondary" :data-show="show.id" @click="emit('show', show.id)">{{ show.title }} ↗</button></div></section>
        </template>
      </div>
    </section>
  </main>
</template>
