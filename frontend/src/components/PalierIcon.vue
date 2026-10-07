<template>
  <component
    :is="icon"
    :size="size"
    :stroke-width="strokeWidth"
    class="palier-icon"
  />
</template>

<script setup>
import { computed } from 'vue'
import {
  Sparkles, Zap, Type, AlignLeft, AlignCenter,
  AlignJustify, Scroll, Infinity as LucideInfinity,
  Code2, BookOpen
} from 'lucide-vue-next'

const props = defineProps({
  palier:      { type: String, required: true },
  size:        { type: Number, default: 14 },
  strokeWidth: { type: Number, default: 1.75 },
})

const ICONS = {
  'auto': Sparkles,
  '★':   Zap,
  '0':   Type,
  '1':   AlignLeft,
  '2':   AlignCenter,
  '3':   AlignJustify,
  '4':   Scroll,
  '5':   LucideInfinity,
  'C':   Code2,
  '6':   BookOpen,
}

const icon = computed(() => ICONS[props.palier] ?? AlignLeft)
</script>

<style scoped>
.palier-icon {
  display: inline-block;
  vertical-align: middle;
  color: currentColor;
  flex-shrink: 0;
}
</style>
