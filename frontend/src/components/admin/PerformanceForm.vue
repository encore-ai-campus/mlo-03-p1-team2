<script setup>
import { computed, reactive, ref } from 'vue';
import PosterArt from '@/components/PosterArt.vue';
import { CATEGORIES, MAX_PERFORMANCE_PRICE, photo } from '@/utils';

const props = defineProps({
  performance: { type: Object, default: null },
  busy: { type: Boolean, default: false },
  error: { type: String, default: '' },
});
const emit = defineEmits(['save', 'close', 'clear-error']);
const STYLES = [
  { id: 'city', label: '페스티벌 · 라임' }, { id: 'opera', label: '뮤지컬 · 골드' },
  { id: 'art', label: '전시 · 오렌지' }, { id: 'jazz', label: '재즈 · 블루' },
  { id: 'sport', label: '스포츠 · 네이비' }, { id: 'classic', label: '클래식 · 와인' },
  { id: 'theater', label: '연극 · 퍼플' }, { id: 'dance', label: '모던 · 그레이' },
];
const now = new Date();
const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
const p = props.performance;
const form = reactive({
  title: p?.title || '', category: p?.category || '콘서트', venue: p?.venue || '',
  start_date: p?.start_date || today, end_date: p?.end_date || today, price: p?.price ?? 0,
  slots: p?.slots?.length ? [...p.slots] : ['19:30'],
  image: p?.image ? photo(p.image) : '', english: p?.english || '', sub: p?.sub || '',
  style: p?.style || 'city', badge: p?.badge || '', tag: p?.tag || '',
});
const localError = ref('');
const preview = computed(() => {
  try {
    const url = new URL(form.image);
    if (url.protocol !== 'https:' || url.hostname !== 'images.unsplash.com') return null;
    const image = url.pathname.slice(1);
    if (!/^photo-[A-Za-z0-9-]+$/.test(image)) return null;
    return {
      ...form, image, english: form.english || form.title || 'TIKIT',
      date_label: `${form.start_date.replaceAll('-', '.')} - ${form.end_date.replaceAll('-', '.')}`,
    };
  } catch { return null; }
});

function clearError() { localError.value = ''; emit('clear-error'); }
function addSlot() {
  if (form.slots.length < 24) form.slots.push('');
  clearError();
}
function submit() {
  if (props.busy) return;
  clearError();
  if (form.end_date < form.start_date) { localError.value = '종료일은 시작일보다 빠를 수 없습니다.'; return; }
  if (new Set(form.slots).size !== form.slots.length) { localError.value = '같은 회차를 중복해서 입력할 수 없습니다.'; return; }
  emit('save', { ...form, slots: [...form.slots] });
}
</script>

<template>
  <form class="admin-performance-form" @submit.prevent="submit" @input="clearError" @change="clearError">
    <fieldset :disabled="busy">
      <legend class="admin-form-legend">기본 정보</legend>
      <div class="admin-form-grid">
        <label class="form-field full"><span>공연명 <span class="required">*</span></span><input v-model="form.title" required maxlength="200" placeholder="공연명을 입력해 주세요"></label>
        <label class="form-field"><span>카테고리 <span class="required">*</span></span><select v-model="form.category"><option v-for="c in CATEGORIES.slice(1)" :key="c">{{ c }}</option></select></label>
        <label class="form-field"><span>일반석 가격 (원) <span class="required">*</span></span><input v-model.number="form.price" type="number" min="0" :max="MAX_PERFORMANCE_PRICE" step="1" required></label>
        <label class="form-field full"><span>공연장 <span class="required">*</span></span><input v-model="form.venue" required maxlength="200" placeholder="공연장 이름을 입력해 주세요"></label>
        <label class="form-field"><span>공연 시작일 <span class="required">*</span></span><input v-model="form.start_date" type="date" required></label>
        <label class="form-field"><span>공연 종료일 <span class="required">*</span></span><input v-model="form.end_date" type="date" :min="form.start_date" required></label>
      </div>
      <p class="admin-form-hint">시작일부터 종료일까지 매일 예매할 수 있습니다. 한 공연의 예매 가능 기간은 최대 366일입니다.</p>
      <div class="form-field">
        <span>회차 <span class="required">*</span></span>
        <div class="admin-slot-list">
          <div v-for="(_, i) in form.slots" :key="i" class="admin-slot">
            <input v-model="form.slots[i]" type="time" required :aria-label="`${i + 1}번째 회차`">
            <button type="button" :disabled="form.slots.length === 1" :aria-label="`${i + 1}번째 회차 삭제`" @click="form.slots.splice(i, 1)">×</button>
          </div>
          <button class="admin-add-slot" type="button" :disabled="form.slots.length >= 24" @click="addSlot">＋ 회차 추가</button>
        </div>
      </div>

      <h3 class="admin-form-legend">공연 카드</h3>
      <label class="form-field"><span>포스터 이미지 주소 <span class="required">*</span></span><input v-model="form.image" type="url" maxlength="500" required placeholder="https://images.unsplash.com/photo-…"></label>
      <p class="admin-form-hint">현재 사이트에서 사용하는 Unsplash 이미지 주소를 입력해 주세요.</p>
      <div class="admin-form-grid">
        <label class="form-field"><span>포스터 제목</span><textarea v-model="form.english" rows="3" maxlength="200" placeholder="비워 두면 공연명이 표시됩니다"></textarea></label>
        <label class="form-field"><span>포스터 부제</span><input v-model="form.sub" maxlength="200" placeholder="포스터에 표시할 짧은 문구"></label>
        <label class="form-field"><span>포스터 스타일</span><select v-model="form.style"><option v-for="s in STYLES" :key="s.id" :value="s.id">{{ s.label }}</option></select></label>
        <label class="form-field"><span>포스터 배지</span><input v-model="form.badge" maxlength="100" placeholder="예: 단독 판매"></label>
        <label class="form-field full"><span>목록 태그</span><input v-model="form.tag" maxlength="100" placeholder="예: 티킷 PICK"></label>
      </div>
      <div v-if="preview" class="admin-preview">
        <div class="admin-preview-art"><PosterArt :show="preview" /></div>
        <div><b>공연 카드 미리보기</b><p>홈과 공연 목록에 같은 스타일로 표시됩니다.</p></div>
      </div>
    </fieldset>
    <p v-if="localError || error" class="form-error" role="alert">{{ localError || error }}</p>
    <div class="admin-form-actions">
      <button class="secondary" type="button" :disabled="busy" @click="emit('close')">취소</button>
      <button class="primary" type="submit" :disabled="busy">{{ busy ? '저장 중…' : performance ? '변경 내용 저장' : '공연 등록' }}</button>
    </div>
  </form>
</template>

<style scoped>
fieldset{min-width:0;border:0;padding:0;margin:0}
.admin-form-legend{font-size:15px;font-weight:800;margin:0 0 20px;padding:0}
h3.admin-form-legend{margin-top:28px;padding-top:24px;border-top:1px solid var(--line)}
.admin-form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 18px}
.full{grid-column:1/-1}
.form-field textarea{display:block;width:100%;padding:12px;border:1px solid #e6dfed;border-radius:6px;background:white;font:inherit;font-size:13px;resize:vertical}
.form-field textarea:focus{outline-color:var(--purple)}
.admin-form-hint{font-size:11px;color:var(--muted);line-height:1.8;margin:-5px 0 18px}
.admin-slot-list{display:flex;gap:8px;flex-wrap:wrap}
.admin-slot{display:flex;align-items:center;gap:4px}
.admin-slot input{width:125px}
.admin-slot button{padding:7px;color:#9b7180;font-size:20px}
.admin-add-slot{border:1px solid var(--line);border-radius:6px;padding:9px 14px;color:var(--purple);font-size:12px}
.admin-preview{display:flex;align-items:center;gap:24px;margin-top:20px;padding:20px;background:var(--pale);border-radius:8px}
.admin-preview-art{width:130px;flex:none;isolation:isolate;overflow:hidden;border-radius:6px}
.admin-preview-art :deep(.poster){padding:12px}
.admin-preview-art :deep(.poster-title){font-size:26px}
.admin-preview-art :deep(.poster-label),.admin-preview-art :deep(.poster-sub),.admin-preview-art :deep(.poster-date),.admin-preview-art :deep(.poster-eyebrow){display:none}
.admin-preview b{font-size:13px}
.admin-preview p{font-size:11px;color:#887b94;line-height:1.8}
.admin-form-actions{display:flex;gap:12px;margin-top:24px}
.admin-form-actions button{flex:1;margin:0}
@media(max-width:760px){.admin-form-grid{grid-template-columns:1fr}.admin-preview{gap:15px;padding:15px}.admin-preview-art{width:95px}.admin-preview-art :deep(.poster-title){font-size:20px}}
</style>
