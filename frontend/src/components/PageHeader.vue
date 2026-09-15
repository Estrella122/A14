<script setup>
defineProps({
  eyebrow: { type: String, default: '' },
  title: { type: String, required: true },
  description: { type: String, default: '' },
})
</script>

<template>
  <header class="page-heading">
    <div class="page-heading-copy">
      <p v-if="eyebrow" class="eyebrow">{{ eyebrow }}</p>
      <h1>{{ title }}</h1>
      <p v-if="description" class="page-description">{{ description }}</p>
      <div v-if="$slots.meta" class="page-heading-meta">
        <slot name="meta" />
      </div>
    </div>
    <div v-if="$slots.actions" class="page-heading-actions">
      <slot name="actions" />
    </div>
  </header>
</template>
