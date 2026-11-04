<script setup>
defineProps({ kicker: String, title: String, intro: String });
</script>

<template>
  <div class="panel-head">
    <div class="section-kicker">{{ kicker }}</div>
    <h2>{{ title }}</h2>
    <p v-if="intro" class="modal-intro">{{ intro }}</p>
  </div>
</template>
