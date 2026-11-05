<script setup>
import { onMounted, reactive, ref } from 'vue';
import PanelHead from './PanelHead.vue';
import { useAuthedApi } from '@/composables/useAuthedApi';
import { toast } from '@/composables/useToast';
import { track } from '@/utils/tracker';

const authed = useAuthedApi();
const settings = reactive({ booking_reminders: false, favorite_updates: false });
const items = ref([]);
const loading = ref(true);
const ready = ref(false);
const busy = ref(false);
const error = ref('');
const listError = ref('');

async function loadItems() {
  listError.value = '';
  try { items.value = await authed('/users/me/notifications'); }
  catch (err) { listError.value = err.message; }
}
async function load() {
  loading.value = true;
  error.value = '';
  try {
    Object.assign(settings, await authed('/users/me/notification-settings'));
    ready.value = true;
    await loadItems();
  } catch (err) { error.value = err.message; }
  finally { loading.value = false; }
}
async function save() {
  if (busy.value) return;
  busy.value = true;
  error.value = '';
  try {
    Object.assign(settings, await authed('/users/me/notification-settings', { method: 'PUT', body: { ...settings } }));
    track('notification_settings_update', { ...settings });
    toast('알림 설정을 저장했어요.');
    await loadItems();
  } catch (err) { error.value = err.message; }
  finally { busy.value = false; }
}
onMounted(load);
</script>

<template>
  <PanelHead kicker="NOTIFICATIONS" title="알림 설정" intro="원하는 알림을 켜고 마이페이지에서 다가오는 공연 소식을 확인하세요." />
  <p v-if="loading" class="tickets-loading" role="status">알림 설정을 불러오는 중입니다…</p>
  <template v-else>
    <form v-if="ready" @submit.prevent="save">
      <fieldset :disabled="busy" class="notification-fields">
        <legend class="notification-legend">마이페이지 알림</legend>
        <label class="notification-option">
          <span><b>관람 일정 알림</b><small>결제가 완료된 예매 중 오늘부터 7일 이내의 공연 일정을 보여드려요.</small></span>
          <input v-model="settings.booking_reminders" type="checkbox" role="switch">
        </label>
        <label class="notification-option">
          <span><b>찜한 공연 소식</b><small>진행 중이거나 7일 이내에 시작하는 찜한 공연을 알려드려요.</small></span>
          <input v-model="settings.favorite_updates" type="checkbox" role="switch">
        </label>
        <button type="submit" class="primary">{{ busy ? '저장 중…' : '알림 설정 저장' }}</button>
      </fieldset>
    </form>
    <div v-if="error" class="notification-error">
      <p role="alert">{{ error }}</p><button class="secondary" type="button" :disabled="busy" @click="load">설정 다시 불러오기</button>
    </div>
    <section class="notification-list">
      <h3>내 알림</h3>
      <div v-if="listError"><p role="alert">{{ listError }}</p><button class="secondary" type="button" @click="loadItems">알림 다시 불러오기</button></div>
      <ul v-else-if="items.length">
        <li v-for="item in items" :key="item.id">
          <span class="tag">{{ item.kind === 'booking' ? '관람 일정' : '찜한 공연' }}</span>
          <h4>{{ item.title }}</h4><p>{{ item.message }}</p>
          <RouterLink :to="item.kind === 'booking' ? '/mypage/orders' : { path: '/', query: { show: item.performance_id } }">{{ item.kind === 'booking' ? '예매 내역 확인' : '공연 자세히 보기' }} ↗</RouterLink>
        </li>
      </ul>
      <p v-else class="modal-intro">새로운 알림이 없어요. 알림을 켜고 저장하면 해당하는 공연 소식을 여기서 확인할 수 있어요.</p>
    </section>
  </template>
</template>

<style scoped>
.notification-fields { padding: 0; border: 0; margin: 0; }
.notification-legend { font-size: 15px; font-weight: 700; padding: 0; margin-bottom: 8px; }
.notification-option { display: flex; justify-content: space-between; align-items: center; gap: 20px; padding: 22px 0; border-bottom: 1px solid var(--line); cursor: pointer; }
.notification-option b { font-size: 14px; } .notification-option small { display: block; font-size: 12px; color: #7e718a; margin-top: 8px; line-height: 1.7; }
input { width: 22px; height: 22px; flex-shrink: 0; accent-color: var(--purple); }
.primary { max-width: 260px; } .notification-list { margin-top: 36px; } h3 { font-size: 17px; }
ul { list-style: none; padding: 0; } li { padding: 20px; border: 1px solid var(--line); border-radius: 10px; margin-top: 12px; }
h4 { margin: 14px 0 8px; } li p { font-size: 12px; color: #7e718a; line-height: 1.8; } li a { font-size: 12px; color: var(--purple); }
.notification-error { color: #a33744; font-size: 13px; }
</style>
