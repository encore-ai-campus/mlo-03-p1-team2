<script setup>
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import BaseModal from '@/components/BaseModal.vue';
import PerformanceForm from '@/components/admin/PerformanceForm.vue';
import { useAdminApi } from '@/composables/useAdminApi';
import { toast } from '@/composables/useToast';
import { CATEGORIES, photo, won } from '@/utils';

const SORTS = [{ id: 'date', label: '공연일순' }, { id: 'title', label: '공연명순' }, { id: 'price', label: '낮은 가격순' }];
const PAGE_SIZE = 10;
const route = useRoute();
const router = useRouter();
const api = useAdminApi();
const items = ref([]);
const total = ref(0);
const loading = ref(true);
const error = ref('');
const keyword = ref('');
const modal = ref(null);
const modalError = ref('');
const busy = ref(false);

const category = computed({
  get: () => (CATEGORIES.includes(route.query.category) ? route.query.category : '전체'),
  set: value => filter({ category: value === '전체' ? undefined : value }),
});
const search = computed(() => (typeof route.query.q === 'string' ? route.query.q.trim().slice(0, 100) : ''));
const sort = computed({
  get: () => (SORTS.some(s => s.id === route.query.sort) ? route.query.sort : 'date'),
  set: value => filter({ sort: value === 'date' ? undefined : value }),
});
const page = computed(() => {
  const value = typeof route.query.page === 'string' ? Number(route.query.page) : 1;
  return Number.isSafeInteger(value) && value > 0 && value <= 1_000_000 ? value : 1;
});
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)));
const pages = computed(() => {
  const start = Math.max(1, Math.min(page.value - 2, pageCount.value - 4));
  return Array.from({ length: Math.min(5, pageCount.value) }, (_, i) => start + i);
});
watch(search, value => { keyword.value = value; }, { immediate: true });

function filter(changes) {
  router.push({ path: '/admin/performances', query: { ...route.query, ...changes, page: undefined } });
}
function resetFilters() { keyword.value = ''; router.push('/admin/performances'); }
function goToPage(value) {
  if (value < 1 || value > pageCount.value || value === page.value) return;
  router.push({ path: '/admin/performances', query: { ...route.query, page: value === 1 ? undefined : value } });
}

/* ---------- 관리자 목록 ---------- */
let listRequest = 0;
async function load() {
  const id = ++listRequest;
  loading.value = true;
  error.value = '';
  const params = new URLSearchParams({ sort: sort.value, page: String(page.value), page_size: String(PAGE_SIZE) });
  if (search.value) params.set('q', search.value);
  if (category.value !== '전체') params.set('category', category.value);
  try {
    const result = await api(`/admin/performances?${params}`);
    if (id !== listRequest) return;
    items.value = result.items;
    total.value = result.total;
    const last = Math.max(1, Math.ceil(result.total / PAGE_SIZE));
    if (page.value > last) {
      await router.replace({ path: '/admin/performances', query: { ...route.query, page: last === 1 ? undefined : last } });
    }
  } catch (err) {
    if (id === listRequest) { items.value = []; error.value = err.message; }
  } finally {
    if (id === listRequest) loading.value = false;
  }
}
watch([search, category, sort, page], load, { immediate: true });

/* ---------- 등록·수정·삭제 ---------- */
function openModal(type, performance = null) {
  if (busy.value) return;
  modalError.value = '';
  modal.value = { type, performance };
}
function closeModal() { if (!busy.value) modal.value = null; }

async function save(body) {
  if (busy.value || !modal.value) return;
  busy.value = true;
  modalError.value = '';
  const editing = modal.value.type === 'edit';
  const path = editing ? `/admin/performances/${encodeURIComponent(modal.value.performance.id)}` : '/admin/performances';
  try {
    await api(path, { method: editing ? 'PUT' : 'POST', body });
    modal.value = null;
    toast(editing ? '공연 정보를 수정했어요.' : '새로운 공연을 등록했어요.');
    await load();
  } catch (err) {
    modalError.value = err.message;
  } finally {
    busy.value = false;
  }
}

async function remove() {
  if (busy.value || modal.value?.type !== 'delete') return;
  busy.value = true;
  modalError.value = '';
  try {
    await api(`/admin/performances/${encodeURIComponent(modal.value.performance.id)}`, { method: 'DELETE' });
    modal.value = null;
    toast('공연을 삭제했어요.');
    await load();
  } catch (err) {
    modalError.value = err.message;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <main class="admin-page">
    <div class="wrap admin-shell">
      <div class="admin-heading">
        <div><div class="section-kicker">ADMINISTRATION</div><h1>공연 관리 <span>✦</span></h1><p>공연을 등록하고, 공연 정보와 관람 일정을 관리하세요.</p></div>
        <button class="admin-primary" type="button" :disabled="busy" @click="openModal('create')">＋ 공연 등록</button>
      </div>

      <section class="admin-panel" aria-label="공연 관리 목록">
        <div class="admin-filter-bar">
          <form class="admin-search" role="search" aria-label="관리자 공연 검색" @submit.prevent="filter({ q: keyword.trim().slice(0, 100) || undefined })">
            <input v-model="keyword" type="search" name="q" maxlength="100" placeholder="공연명 또는 공연장 검색" aria-label="공연명 또는 공연장">
            <button type="submit">검색</button>
          </form>
          <div class="admin-filters">
            <select v-model="category" aria-label="공연 카테고리"><option v-for="c in CATEGORIES" :key="c">{{ c }}</option></select>
            <select v-model="sort" aria-label="공연 정렬"><option v-for="s in SORTS" :key="s.id" :value="s.id">{{ s.label }}</option></select>
            <button class="text-link" type="button" @click="resetFilters">초기화 ↺</button>
          </div>
        </div>
        <div class="admin-summary" role="status"><span v-if="loading">공연을 불러오고 있어요.</span><span v-else-if="!error">총 <b>{{ total.toLocaleString('ko-KR') }}</b>개의 공연</span><span>예매 내역이 있는 공연은 삭제할 수 없습니다.</span></div>

        <div v-if="error" class="admin-empty" role="alert"><h2>공연을 불러오지 못했어요.</h2><p>{{ error }}</p><button class="admin-primary" type="button" @click="load">다시 불러오기</button></div>
        <p v-else-if="loading" class="tickets-loading">공연 목록을 확인하고 있어요…</p>
        <template v-else-if="items.length">
          <div class="admin-table-scroll">
            <table class="admin-table">
              <caption>등록된 공연 목록</caption>
              <thead><tr><th scope="col">공연</th><th scope="col">공연장</th><th scope="col">관람 기간</th><th scope="col">가격</th><th scope="col">회차</th><th scope="col">관리</th></tr></thead>
              <tbody>
                <tr v-for="s in items" :key="s.id">
                  <td><div class="admin-show"><img :src="photo(s.image, 120)" alt="" loading="lazy"><div><span class="tag">{{ s.category }}</span><b>{{ s.title }}</b></div></div></td>
                  <td>{{ s.venue }}</td>
                  <td class="admin-period">{{ s.start_date.replaceAll('-', '.') }}<br>~ {{ s.end_date.replaceAll('-', '.') }}</td>
                  <td class="admin-price">{{ won(s.price) }}</td>
                  <td>{{ s.slots.length }}개</td>
                  <td><div class="admin-row-actions"><button type="button" :disabled="busy" :aria-label="`${s.title} 수정`" @click="openModal('edit', s)">수정</button><button class="admin-delete" type="button" :disabled="busy" :aria-label="`${s.title} 삭제`" @click="openModal('delete', s)">삭제</button></div></td>
                </tr>
              </tbody>
            </table>
          </div>
          <nav v-if="pageCount > 1" class="admin-pagination" aria-label="공연 관리 목록 페이지">
            <button type="button" :disabled="page === 1" aria-label="이전 페이지" @click="goToPage(page - 1)">←</button>
            <button v-for="n in pages" :key="n" type="button" :class="{ active: n === page }" :aria-current="n === page ? 'page' : undefined" :aria-label="`${n} 페이지`" @click="goToPage(n)">{{ n }}</button>
            <button type="button" :disabled="page === pageCount" aria-label="다음 페이지" @click="goToPage(page + 1)">→</button>
          </nav>
        </template>
        <div v-else class="admin-empty"><span class="admin-empty-icon" aria-hidden="true">✧</span><h2>표시할 공연이 없어요.</h2><p>검색 조건을 바꾸거나 새로운 공연을 등록해 주세요.</p><button class="text-link" type="button" @click="resetFilters">전체 공연 보기 ↗</button></div>
      </section>
    </div>
  </main>

  <BaseModal v-if="modal && modal.type !== 'delete'" class="admin-editor" :title="modal.type === 'edit' ? '공연 정보 수정' : '새로운 공연 등록'" @close="closeModal">
    <PerformanceForm :key="modal.performance?.id || 'create'" :performance="modal.performance" :busy="busy" :error="modalError" @save="save" @close="closeModal" @clear-error="modalError = ''" />
  </BaseModal>
  <BaseModal v-else-if="modal?.type === 'delete'" title="공연 삭제" @close="closeModal">
    <div class="admin-delete-confirm"><span class="tag">{{ modal.performance.category }}</span><h3>{{ modal.performance.title }}</h3><p>이 공연을 삭제하시겠어요?</p><p>연결된 찜과 조회 기록도 함께 삭제됩니다.<br>예매 내역이 있는 공연은 삭제할 수 없습니다.</p><p v-if="modalError" class="form-error" role="alert">{{ modalError }}</p><div class="admin-confirm-actions"><button class="secondary" type="button" :disabled="busy" @click="closeModal">돌아가기</button><button class="primary admin-danger" type="button" :disabled="busy" @click="remove">{{ busy ? '삭제 중…' : '공연 삭제' }}</button></div></div>
  </BaseModal>
</template>

<style scoped>
.admin-page{background:#faf9fc;min-height:70vh;border-top:1px solid var(--line)}
.admin-shell{padding-top:40px;padding-bottom:64px}
.admin-heading{display:flex;align-items:center;justify-content:space-between;gap:24px;margin-bottom:28px}
.admin-heading h1{font-size:30px;font-weight:800;letter-spacing:-1.2px;margin:9px 0 10px}
.admin-heading h1 span{color:var(--purple)}
.admin-heading p{font-size:13px;line-height:1.8;color:#887b94;margin:0}
.admin-primary{background:var(--purple);color:white;border-radius:6px;padding:13px 22px;font-size:12px;font-weight:700;white-space:nowrap}
.admin-primary:hover{color:white;background:var(--purple-dark)}
.admin-panel{padding:26px;background:white;border:1px solid var(--line);border-radius:12px}
.admin-filter-bar{display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap}
.admin-search{display:flex;align-items:center;gap:8px;max-width:380px;flex:1;min-width:220px;border:1px solid #e9e4f3;border-radius:6px;padding:5px 6px 5px 14px;background:#faf9fc}
.admin-search:focus-within{border-color:var(--purple)}
.admin-search input{border:0;background:none;outline:none;min-width:0;width:100%;font-size:12px}
.admin-search button{background:var(--pale);color:var(--purple);padding:9px 14px;font-size:11px;font-weight:600;border-radius:4px;flex:none}
.admin-filters{display:flex;align-items:center;gap:12px}
.admin-filters select{border:1px solid var(--line);border-radius:5px;padding:9px;background:white;font-size:12px;color:#7d7486;max-width:140px}
.admin-summary{display:flex;justify-content:space-between;gap:15px;flex-wrap:wrap;padding:22px 0 16px;color:var(--muted);font-size:11px;line-height:1.8}
.admin-summary b{color:var(--purple)}
.admin-table-scroll{overflow-x:auto}
.admin-table{width:100%;min-width:820px;border-collapse:collapse;text-align:left;font-size:12px}
.admin-table caption{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
.admin-table th{background:#faf8fd;color:#8b7f96;font-weight:600;padding:13px 12px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);white-space:nowrap}
.admin-table td{padding:18px 12px;border-bottom:1px solid var(--line);line-height:1.7;overflow-wrap:anywhere}
.admin-table th:first-child{width:33%}
.admin-show{display:flex;align-items:center;gap:14px}
.admin-show img{width:45px;height:59px;object-fit:cover;border-radius:4px;flex:none;background:var(--pale)}
.admin-show b{display:block;font-size:13px;font-weight:700;line-height:1.6;margin-top:6px}
.admin-period{font-size:11px;color:#8b7f96;white-space:nowrap}
.admin-price{font-weight:600;white-space:nowrap}
.admin-row-actions{display:flex;gap:6px}
.admin-row-actions button{border:1px solid var(--line);border-radius:4px;padding:7px 10px;font-size:11px;white-space:nowrap}
.admin-row-actions .admin-delete{color:#b7435e;border-color:#efdae1}
.admin-empty{text-align:center;padding:60px 20px}
.admin-empty h2{font-size:19px;margin:0 0 12px}
.admin-empty p{color:var(--muted);font-size:12px;line-height:1.8;margin:0 0 20px}
.admin-empty-icon{display:block;color:var(--purple);font-size:35px;margin-bottom:18px}
.admin-pagination{display:flex;justify-content:center;gap:7px;margin-top:28px}
.admin-pagination button{min-width:34px;height:34px;border:1px solid var(--line);border-radius:5px;font-size:12px}
.admin-pagination button.active{background:var(--purple);border-color:var(--purple);color:white}
.admin-pagination button:disabled{opacity:.35;cursor:default}
.admin-editor{width:min(820px,calc(100vw - 32px));max-width:none}
.admin-delete-confirm h3{font-size:19px;margin:14px 0;line-height:1.5}
.admin-delete-confirm>p{font-size:13px;line-height:1.8;color:#887b94}
.admin-confirm-actions{display:flex;gap:12px;margin-top:24px}
.admin-confirm-actions button{flex:1;margin:0}
.admin-danger{background:#b83d5b}
.admin-danger:hover{background:#9a2c47}
@media(max-width:760px){.admin-shell{padding-top:28px;padding-bottom:40px}.admin-heading{align-items:flex-start;flex-direction:column;gap:18px}.admin-heading h1{font-size:26px}.admin-heading p{font-size:12px}.admin-panel{padding:18px}.admin-search{max-width:none;flex-basis:100%;min-width:0}.admin-filters{width:100%;gap:8px}.admin-filters .text-link{margin-left:auto}.admin-filters select{font-size:11px;max-width:120px}.admin-summary{gap:4px;flex-direction:column}.admin-table{min-width:780px}}
</style>
