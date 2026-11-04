<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
defineProps({ title: String })
const emit = defineEmits(['close'])
const dialog = ref(null)
let previousFocus
onMounted(() => {
  previousFocus = document.activeElement
  dialog.value.showModal()
})
onBeforeUnmount(() => {
  dialog.value?.close()
  if (previousFocus?.isConnected) previousFocus.focus()
})
function backdrop(event) {
  if (event.target !== dialog.value) return
  const r = dialog.value.getBoundingClientRect()
  if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) emit('close')
}
</script>

<template>
  <dialog id="modal" ref="dialog" aria-labelledby="modalTitle" @cancel.prevent="emit('close')" @click="backdrop">
    <div id="modalContent">
      <div class="modal-header"><h2 id="modalTitle">{{ title }}</h2><button class="close-modal" aria-label="창 닫기" @click="emit('close')">×</button></div>
      <div class="modal-body"><slot /></div>
    </div>
  </dialog>
</template>
