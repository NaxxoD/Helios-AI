<template>
  <svg :width="size" :height="size" viewBox="0 0 48 48" fill="none" aria-hidden="true">
    <defs>
      <linearGradient :id="gradId" x1="8" y1="8" x2="40" y2="40" gradientUnits="userSpaceOnUse">
        <stop offset="0" stop-color="#34D8A0"/>
        <stop offset="1" stop-color="#E8843C"/>
      </linearGradient>
    </defs>
    <circle cx="24" cy="24" r="18.5" :stroke="gradRef" stroke-width="2.6"/>
    <g class="ap-rays" :stroke="gradRef" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
      <path d="M24 8.2 33.4 24"/>
      <path d="M38.5 28.6 20.3 28.6"/>
      <path d="M30.8 41 21.7 25"/>
      <path d="M14.6 39.8 24 24"/>
      <path d="M9.5 19.4 27.7 19.4"/>
      <path d="M17.2 7 26.3 23"/>
    </g>
    <circle cx="24" cy="24" r="5.3" :fill="gradRef"/>
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  size: { type: Number, default: 22 },
  uid:  { type: String, default: 'default' },
})

const gradId  = computed(() => `helios-ap-${props.uid}`)
const gradRef = computed(() => `url(#helios-ap-${props.uid})`)
</script>
