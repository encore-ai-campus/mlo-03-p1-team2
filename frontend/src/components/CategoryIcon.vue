<script setup>
defineProps({ category: { type: String, required: true } });
</script>

<template>
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <template v-if="category === '콘서트'">
      <path d="M9 18V5l12-2v13M9 9l12-2" /><ellipse cx="6" cy="18" rx="3" ry="2.5" /><ellipse cx="18" cy="16" rx="3" ry="2.5" />
    </template>
    <template v-else-if="category === '뮤지컬'">
      <path d="M3 4c4 2 8 2 12 0v8c0 5-6 8-6 8s-6-3-6-8Z" /><path d="m6 10 2 1m3 0 2-1M7 15q2 2 4 0M18 6l3-1v8c0 4-4 7-4 7" />
    </template>
    <template v-else-if="category === '스포츠'">
      <circle cx="12" cy="12" r="9" /><path d="m9 9 6-1 2 5-5 4-5-4ZM12 3 9 9M21 11l-4 2M15 20l-3-3M4 16l3-3M4 7l5 2" />
    </template>
    <template v-else-if="category === '전시'">
      <rect x="3" y="4" width="18" height="16" rx="1" /><path d="m4 17 6-6 4 4 3-3 4 4" /><circle cx="16" cy="8" r="1.5" />
    </template>
    <template v-else-if="category === '클래식'">
      <path d="M8 5c4 3 8 1 12 3v12H3v-8c0-4 5-3 5-7ZM3 15h17M7 15v5m4-5v5m4-5v5M8 5V2" />
    </template>
    <template v-else>
      <path d="M4 4h16v16H4ZM4 5l8 7 8-7M4 17l5-7m11 7-5-7M12 12v8" />
    </template>
  </svg>
</template>
