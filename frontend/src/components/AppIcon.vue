<script setup>
defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 20 },
  strokeWidth: { type: [Number, String], default: 1.8 },
})
</script>

<template>
  <svg
    class="app-icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-if="name === 'dashboard'">
      <rect x="3" y="3" width="7" height="7" rx="2" />
      <rect x="14" y="3" width="7" height="7" rx="2" />
      <rect x="3" y="14" width="7" height="7" rx="2" />
      <rect x="14" y="14" width="7" height="7" rx="2" />
    </template>
    <template v-else-if="name === 'database'">
      <ellipse cx="12" cy="5" rx="8" ry="3" />
      <path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5" />
      <path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" />
    </template>
    <template v-else-if="name === 'spark'">
      <path d="m12 3 1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3Z" />
      <path d="m19 15 .8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z" />
      <path d="m5 14 .8 2.2L8 17l-2.2.8L5 20l-.8-2.2L2 17l2.2-.8L5 14Z" />
    </template>
    <template v-else-if="name === 'clean'">
      <path d="M3 20h12" />
      <path d="m5 16 9-9 4 4-9 9H5v-4Z" />
      <path d="m13 8 4 4" />
      <path d="M16 4h5M18.5 1.5v5" />
    </template>
    <template v-else-if="name === 'segments'">
      <path d="M3 17 7 12l4 3 5-8 5 4" />
      <path d="M3 4v16h18" />
      <path d="M8 5v14M15 5v14" stroke-dasharray="2 3" />
    </template>
    <template v-else-if="name === 'network'">
      <circle cx="5" cy="12" r="2.5" />
      <circle cx="18" cy="6" r="2.5" />
      <circle cx="18" cy="18" r="2.5" />
      <path d="m7.3 10.9 8.4-3.8M7.3 13.1l8.4 3.8" />
    </template>
    <template v-else-if="name === 'model'">
      <path d="M4 19V9M10 19V5M16 19v-7M22 19H2" />
      <path d="m3 7 6-4 6 6 6-5" />
    </template>
    <template v-else-if="name === 'loop'">
      <path d="M20 7h-7a5 5 0 0 0-5 5v1" />
      <path d="m17 4 3 3-3 3" />
      <path d="M4 17h7a5 5 0 0 0 5-5v-1" />
      <path d="m7 20-3-3 3-3" />
    </template>
    <template v-else-if="name === 'report'">
      <path d="M6 2h8l4 4v16H6z" />
      <path d="M14 2v5h5M9 12h6M9 16h6" />
    </template>
    <template v-else-if="name === 'check'">
      <path d="m5 12 4 4L19 6" />
    </template>
    <template v-else-if="name === 'alert'">
      <path d="M12 3 2.8 19h18.4L12 3Z" />
      <path d="M12 9v4M12 17h.01" />
    </template>
    <template v-else-if="name === 'play'">
      <circle cx="12" cy="12" r="9" />
      <path d="m10 8 6 4-6 4V8Z" />
    </template>
    <template v-else-if="name === 'pause'">
      <circle cx="12" cy="12" r="9" />
      <path d="M9.5 8.5v7M14.5 8.5v7" />
    </template>
    <template v-else-if="name === 'upload'">
      <path d="M12 16V4M7 9l5-5 5 5M4 15v5h16v-5" />
    </template>
    <template v-else-if="name === 'download'">
      <path d="M12 4v12M7 11l5 5 5-5M4 20h16" />
    </template>
    <template v-else-if="name === 'chevron'">
      <path d="m9 6 6 6-6 6" />
    </template>
    <template v-else-if="name === 'arrow'">
      <path d="M5 12h14M14 7l5 5-5 5" />
    </template>
    <template v-else-if="name === 'clock'">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </template>
    <template v-else-if="name === 'shield'">
      <path d="M12 3 4.5 6v5c0 5 3.2 8.2 7.5 10 4.3-1.8 7.5-5 7.5-10V6L12 3Z" />
      <path d="m9 12 2 2 4-4" />
    </template>
    <template v-else-if="name === 'bell'">
      <path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 8h18c0-1-3-1-3-8" />
      <path d="M10 21h4" />
    </template>
    <template v-else-if="name === 'more'">
      <circle cx="5" cy="12" r="1" fill="currentColor" stroke="none" />
      <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" />
      <circle cx="19" cy="12" r="1" fill="currentColor" stroke="none" />
    </template>
    <template v-else-if="name === 'file'">
      <path d="M6 2h8l4 4v16H6zM14 2v5h5" />
    </template>
    <template v-else-if="name === 'trash'">
      <path d="M4 7h16M9 3h6l1 4H8l1-4ZM7 7l1 14h8l1-14M10 11v6M14 11v6" />
    </template>
    <template v-else>
      <circle cx="12" cy="12" r="9" />
    </template>
  </svg>
</template>
