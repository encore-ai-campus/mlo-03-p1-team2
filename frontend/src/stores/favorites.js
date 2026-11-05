import { defineStore } from 'pinia';
import { ref, watch } from 'vue';
import { useAuthStore } from './auth';

export const useFavoritesStore = defineStore('favorites', () => {
  const auth = useAuthStore();
  const ids = ref([]);
  const pending = ref([]);
  const loading = ref(false);
  const ready = ref(false);
  let revision = 0;
  let accountGeneration = 0;
  let loadingPromise = null;

  watch(() => auth.profile?.id, () => {
    revision++;
    accountGeneration++;
    ids.value = [];
    pending.value = [];
    ready.value = false;
    loading.value = false;
    loadingPromise = null;
  }, { flush: 'sync' });

  function load() {
    if (loadingPromise) return loadingPromise;
    const current = ++revision;
    if (!auth.profile) { ids.value = []; return Promise.resolve(); }
    loading.value = true;
    const promise = auth.api('/favorites').then(result => {
      if (current === revision) { ids.value = result; ready.value = true; }
    }).finally(() => {
      if (loadingPromise === promise) { loading.value = false; loadingPromise = null; }
    });
    loadingPromise = promise;
    return promise;
  }

  async function toggle(id) {
    if (!auth.profile) throw new Error('로그인 후 찜한 공연을 저장할 수 있어요.');
    const generation = accountGeneration;
    if (!ready.value || loadingPromise) await (loadingPromise || load());
    if (generation !== accountGeneration || pending.value.includes(id)) return;
    const saved = ids.value.includes(id);
    pending.value = [...pending.value, id];
    try {
      await auth.api(`/favorites/${encodeURIComponent(id)}`, { method: saved ? 'DELETE' : 'PUT' });
      if (generation !== accountGeneration) return;
      revision++;
      ids.value = saved ? ids.value.filter(value => value !== id) : [...ids.value, id];
      return !saved;
    } finally {
      if (generation === accountGeneration) pending.value = pending.value.filter(value => value !== id);
    }
  }

  return { ids, pending, loading, load, toggle };
});
