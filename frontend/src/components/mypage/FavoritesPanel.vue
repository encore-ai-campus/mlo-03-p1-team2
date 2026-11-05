<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import PanelHead from './PanelHead.vue';
import PerformanceCard from '@/components/PerformanceCard.vue';
import { useAuthStore } from '@/stores/auth';
import { useFavoritesStore } from '@/stores/favorites';
import { toast } from '@/composables/useToast';

const auth = useAuthStore();
const favorites = useFavoritesStore();
const router = useRouter();
const shows = ref([]);
const loading = ref(true);
const error = ref('');
const liked = computed(() => shows.value.filter(show => favorites.ids.includes(show.id)));

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const [all] = await Promise.all([auth.api('/performances'), favorites.load()]);
    shows.value = all;
  } catch (err) { error.value = err.message; }
  finally { loading.value = false; }
}

async function toggle(id) {
  try {
    const saved = await favorites.toggle(id);
    if (saved === false) toast('찜한 공연에서 해제했어요.');
  } catch (err) { toast(err.message); }
}

onMounted(load);
</script>

<template>
  <PanelHead kicker="FAVORITES" title="찜한 공연" intro="하트로 담아 둔 공연을 모았어요. 공연을 누르면 상세 정보와 예매를 확인할 수 있어요." />
  <div :aria-busy="String(loading)">
    <p v-if="loading" class="tickets-loading" role="status">찜한 공연을 불러오는 중입니다…</p>
    <div v-else-if="error" class="tickets-empty">
      <p role="alert">{{ error }}</p>
      <button type="button" class="secondary" @click="load">다시 불러오기</button>
    </div>
    <template v-else-if="liked.length">
      <p class="modal-intro">총 {{ liked.length }}개의 공연을 찜했어요.</p>
      <div class="favorites-grid">
        <PerformanceCard v-for="show in liked" :key="show.id" :show="show" saved
          :busy="favorites.pending.includes(show.id)"
          @favorite="toggle" @open="id => router.push({ path: '/', query: { show: id } })" />
      </div>
    </template>
    <div v-else class="tickets-empty">
      <h3>아직 찜한 공연이 없어요</h3>
      <p>마음에 드는 공연의 하트를 눌러 담아 보세요.</p>
      <RouterLink class="primary" to="/">공연 둘러보기</RouterLink>
    </div>
  </div>
</template>

<style scoped>
.favorites-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 28px 20px; }
@media (min-width: 1200px) { .favorites-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 420px) { .favorites-grid { grid-template-columns: 1fr; } }
</style>
