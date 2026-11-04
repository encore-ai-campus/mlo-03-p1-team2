<script setup>
import { ref } from 'vue';

// 비밀번호 입력칸 + 보기/숨기기 버튼
defineProps({
  label: { type: String, required: true },
  name: { type: String, required: true },
  autocomplete: { type: String, default: 'current-password' },
  placeholder: { type: String, default: '' },
  required: { type: Boolean, default: true },
});
const model = defineModel({ type: String, default: '' });
const visible = ref(false);
</script>

<template>
  <label class="form-field">
    <span>{{ label }} <span v-if="required" class="required">*</span></span>
    <span class="password-control">
      <input
        v-model="model" :name="name" :type="visible ? 'text' : 'password'" :required="required"
        maxlength="128" :autocomplete="autocomplete" :placeholder="placeholder"
      >
      <button
        type="button" :aria-pressed="String(visible)" :aria-label="`${label} ${visible ? '숨기기' : '표시'}`"
        @click="visible = !visible"
      >{{ visible ? '숨기기' : '보기' }}</button>
    </span>
  </label>
</template>
