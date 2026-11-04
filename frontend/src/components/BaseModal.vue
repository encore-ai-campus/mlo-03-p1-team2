<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';

// <dialog> 기반 모달. 부모가 v-if로 열고, close 이벤트를 받으면 닫습니다.
const props = defineProps({ title: { type: String, required: true } });
const emit = defineEmits(['close']);
const dialog = ref(null);

onMounted(() => { dialog.value.showModal(); });
onBeforeUnmount(() => { if (dialog.value?.open) dialog.value.close(); });
// 단계가 바뀌면(제목 변경) 맨 위부터 보이게 합니다.
watch(() => props.title, () => { if (dialog.value) dialog.value.scrollTop = 0; });

// 바깥(배경) 클릭 시 닫기
function onClick(e) {
  if (e.target !== dialog.value) return;
  const r = dialog.value.getBoundingClientRect();
  if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) emit('close');
}
// Esc 키: 브라우저가 직접 닫지 않게 막고 부모에게 알립니다.
function onCancel(e) { e.preventDefault(); emit('close'); }
</script>

<template>
  <dialog ref="dialog" aria-labelledby="modalTitle" @click="onClick" @cancel="onCancel">
    <div>
      <div class="modal-header">
        <h2 id="modalTitle">{{ title }}</h2>
        <button class="close-modal" type="button" aria-label="창 닫기" @click="emit('close')">×</button>
      </div>
      <div class="modal-body"><slot /></div>
    </div>
  </dialog>
</template>
