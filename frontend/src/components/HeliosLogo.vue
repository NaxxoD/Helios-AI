<template>
  <!--
    Helios logo — "Solar GPU" mark.
    Usage:
      <HeliosLogo />                       → gradient brand mark, 1em square
      <HeliosLogo :size="34" />            → fixed pixel size
      <HeliosLogo mono />                  → single-colour, inherits currentColor
      <HeliosLogo simplified />            → favicon-grade (no inner traces), use ≤ 32px
    The gradient id is made unique per instance so multiple logos on one page don't clash.
  -->
  <svg
    :width="size" :height="size"
    viewBox="0 0 64 64" fill="none"
    role="img" aria-label="Helios"
    xmlns="http://www.w3.org/2000/svg"
  >
    <defs v-if="!mono">
      <linearGradient :id="gid" x1="8" y1="6" x2="56" y2="58" gradientUnits="userSpaceOnUse">
        <stop offset="0" stop-color="#34D8A0" />
        <stop offset="1" stop-color="#E8843C" />
      </linearGradient>
    </defs>

    <!-- rays -->
    <g :stroke="stroke" :stroke-width="simplified ? 3 : 2.6" stroke-linecap="round">
      <path d="M32 2.5v7" /><path d="M32 54.5v7" /><path d="M2.5 32h7" /><path d="M54.5 32h7" />
      <path d="M11 11l5 5" /><path d="M48 48l5 5" /><path d="M53 11l-5 5" /><path d="M11 53l5-5" />
    </g>

    <!-- GPU die -->
    <rect x="18" y="18" width="28" height="28" :rx="simplified ? 7 : 6" :stroke="stroke" :stroke-width="simplified ? 3.2 : 2.8" />

    <template v-if="!simplified">
      <!-- pins -->
      <g :stroke="stroke" stroke-width="2.2" stroke-linecap="round">
        <path d="M25 18v-3.5" /><path d="M32 18v-3.5" /><path d="M39 18v-3.5" />
        <path d="M25 46v3.5" /><path d="M32 46v3.5" /><path d="M39 46v3.5" />
        <path d="M18 25h-3.5" /><path d="M18 32h-3.5" /><path d="M18 39h-3.5" />
        <path d="M46 25h3.5" /><path d="M46 32h3.5" /><path d="M46 39h3.5" />
      </g>
      <!-- circuit traces -->
      <g :stroke="stroke" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M32 28v-4" /><path d="M32 36v4" /><path d="M28 32h-4" /><path d="M36 32h4" />
        <path d="M24 24h4v4" /><path d="M40 24h-4v4" /><path d="M24 40h4v-4" /><path d="M40 40h-4v-4" />
      </g>
      <!-- pads -->
      <g :fill="fill">
        <circle cx="24" cy="24" r="1.5" /><circle cx="40" cy="24" r="1.5" />
        <circle cx="24" cy="40" r="1.5" /><circle cx="40" cy="40" r="1.5" />
      </g>
    </template>

    <!-- core -->
    <rect
      :x="simplified ? 27 : 28.5" :y="simplified ? 27 : 28.5"
      :width="simplified ? 10 : 7" :height="simplified ? 10 : 7"
      :rx="simplified ? 2.4 : 1.8" :fill="fill"
    />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  size:       { type: [Number, String], default: '1em' },
  mono:       { type: Boolean, default: false }, // inherit currentColor instead of gradient
  simplified: { type: Boolean, default: false }, // favicon-grade, drop inner detail
})

// unique gradient id per instance
const gid = `helios-grad-${Math.random().toString(36).slice(2, 8)}`
const stroke = computed(() => (props.mono ? 'currentColor' : `url(#${gid})`))
const fill   = computed(() => (props.mono ? 'currentColor' : `url(#${gid})`))
</script>
