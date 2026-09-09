<script setup>
defineProps({
  tone: { type: String, default: 'neutral' },
  dot: { type: Boolean, default: false },
})
</script>

<template>
  <span class="status-pill" :class="[`is-${tone}`, { 'has-dot': dot }]">
    <span v-if="dot" class="status-dot" aria-hidden="true"></span>
    <slot />
  </span>
</template>
