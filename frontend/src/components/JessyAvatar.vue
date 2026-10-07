<template>
  <div
    class="jessy-avatar"
    :style="{ width: size + 'px', height: size + 'px' }"
    :aria-label="'Avatar de Jessy'"
  >
    <svg
      :width="size"
      :height="size"
      viewBox="0 0 100 100"
      xmlns="http://www.w3.org/2000/svg"
    >
      <!-- Glow ring -->
      <circle cx="50" cy="50" r="47" fill="url(#avatarGlow)" opacity="0.6"/>

      <!-- Background circle -->
      <circle cx="50" cy="50" r="46" fill="url(#avatarBg)" stroke="url(#avatarRing)" stroke-width="1.5"/>

      <!-- Neck -->
      <rect x="40" y="67" width="20" height="13" rx="4" fill="#8B5E3C"/>

      <!-- Shoulders / top -->
      <ellipse cx="50" cy="92" rx="30" ry="14" fill="url(#outfitGrad)"/>

      <!-- Collar detail -->
      <path d="M36 82 Q50 76 64 82" stroke="#a78bfa" stroke-width="1.8" fill="none" stroke-linecap="round"/>

      <!-- Head -->
      <ellipse cx="50" cy="50" rx="21" ry="23" fill="#7D4E2D"/>

      <!-- Cheek highlights -->
      <ellipse cx="34" cy="55" rx="5" ry="3.5" fill="#e07050" opacity="0.35"/>
      <ellipse cx="66" cy="55" rx="5" ry="3.5" fill="#e07050" opacity="0.35"/>

      <!-- Ear left -->
      <ellipse cx="29.5" cy="52" rx="3.5" ry="4.5" fill="#6B3F20"/>
      <ellipse cx="29.5" cy="52" rx="2" ry="2.5" fill="#7D4E2D"/>

      <!-- Ear right -->
      <ellipse cx="70.5" cy="52" rx="3.5" ry="4.5" fill="#6B3F20"/>
      <ellipse cx="70.5" cy="52" rx="2" ry="2.5" fill="#7D4E2D"/>

      <!-- Earring left -->
      <circle cx="27" cy="55" r="2" fill="#fbbf24" opacity="0.95"/>
      <circle cx="27" cy="59" r="1.5" fill="#fbbf24" opacity="0.85"/>

      <!-- Earring right -->
      <circle cx="73" cy="55" r="2" fill="#fbbf24" opacity="0.95"/>
      <circle cx="73" cy="59" r="1.5" fill="#fbbf24" opacity="0.85"/>

      <!-- Afro hair - main volume -->
      <ellipse cx="50" cy="32" rx="26" ry="22" fill="#1a0a00"/>

      <!-- Afro texture layers -->
      <circle cx="30" cy="36" r="10" fill="#231005"/>
      <circle cx="70" cy="36" r="10" fill="#231005"/>
      <circle cx="50" cy="22" r="12" fill="#1e0d03"/>
      <circle cx="37" cy="26" r="8" fill="#2a1208"/>
      <circle cx="63" cy="26" r="8" fill="#2a1208"/>
      <circle cx="28" cy="44" r="7" fill="#241006"/>
      <circle cx="72" cy="44" r="7" fill="#241006"/>

      <!-- Hair shine highlights -->
      <ellipse cx="42" cy="24" rx="4" ry="2.5" fill="white" opacity="0.07" transform="rotate(-20 42 24)"/>
      <ellipse cx="61" cy="22" rx="3" ry="2" fill="white" opacity="0.06" transform="rotate(15 61 22)"/>

      <!-- Hair accessory - green leaf pin -->
      <path d="M62 28 Q70 22 68 30 Q62 32 62 28Z" fill="#34d399" opacity="0.9"/>
      <line x1="62" y1="28" x2="66" y2="26" stroke="#059669" stroke-width="0.8"/>

      <!-- Eyebrows -->
      <path d="M36 47 Q41 44 46 46" stroke="#1a0a00" stroke-width="2.2" fill="none" stroke-linecap="round"/>
      <path d="M54 46 Q59 44 64 47" stroke="#1a0a00" stroke-width="2.2" fill="none" stroke-linecap="round"/>

      <!-- Eyes - big Bratz style -->
      <!-- Left eye -->
      <ellipse cx="41" cy="52" rx="6.5" ry="7" fill="white"/>
      <ellipse cx="41" cy="53" rx="4.8" ry="5.5" fill="#3d1a00"/>
      <ellipse cx="41" cy="53" rx="3.2" ry="3.8" fill="#0a0410"/>
      <circle cx="43" cy="51" r="1.5" fill="white" opacity="0.9"/>
      <circle cx="39.5" cy="55" r="0.8" fill="white" opacity="0.5"/>
      <!-- Left lashes -->
      <path d="M35.5 48 Q36 46 37 47.5" stroke="#1a0a00" stroke-width="1" fill="none" stroke-linecap="round"/>
      <path d="M37.5 47 Q38 45 39 46.5" stroke="#1a0a00" stroke-width="1" fill="none" stroke-linecap="round"/>
      <path d="M39.5 46.5 Q40.5 44.5 41.5 46" stroke="#1a0a00" stroke-width="1" fill="none" stroke-linecap="round"/>
      <path d="M41.5 46.5 Q42.5 44.8 43.5 46.2" stroke="#1a0a00" stroke-width="1" fill="none" stroke-linecap="round"/>
      <path d="M43.5 47 Q44.5 45.5 45.5 47" stroke="#1a0a00" stroke-width="1" fill="none" stroke-linecap="round"/>
      <!-- Left eyeshadow -->
      <ellipse cx="41" cy="48.5" rx="6" ry="2.5" fill="#8b5cf6" opacity="0.3"/>

      <!-- Right eye -->
      <ellipse cx="59" cy="52" rx="6.5" ry="7" fill="white"/>
      <ellipse cx="59" cy="53" rx="4.8" ry="5.5" fill="#3d1a00"/>
      <ellipse cx="59" cy="53" rx="3.2" ry="3.8" fill="#0a0410"/>
      <circle cx="61" cy="51" r="1.5" fill="white" opacity="0.9"/>
      <circle cx="57.5" cy="55" r="0.8" fill="white" opacity="0.5"/>
      <!-- Right lashes -->
      <path d="M54.5 48 Q54 46 55 47.5" stroke="#1a0a00" stroke-width="1" fill="none" stroke-linecap="round"/>
      <path d="M56.5 47 Q57 45 58 46.5" stroke="#1a0a00" stroke-width="1" fill="none" stroke-linecap="round"/>
      <path d="M58.5 46.5 Q59.5 44.5 60.5 46" stroke="#1a0a00" stroke-width="1" fill="none" stroke-linecap="round"/>
      <path d="M60.5 46.5 Q61.5 44.8 62.5 46.2" stroke="#1a0a00" stroke-width="1" fill="none" stroke-linecap="round"/>
      <path d="M62.5 47 Q63.5 45.5 64.5 47" stroke="#1a0a00" stroke-width="1" fill="none" stroke-linecap="round"/>
      <!-- Right eyeshadow -->
      <ellipse cx="59" cy="48.5" rx="6" ry="2.5" fill="#8b5cf6" opacity="0.3"/>

      <!-- Nose -->
      <path d="M48 60 Q50 64 52 60" stroke="#5a2e10" stroke-width="1.5" fill="none" stroke-linecap="round"/>
      <ellipse cx="47" cy="62" rx="2" ry="1.2" fill="#5a2e10" opacity="0.5"/>
      <ellipse cx="53" cy="62" rx="2" ry="1.2" fill="#5a2e10" opacity="0.5"/>

      <!-- Mouth - smile -->
      <path d="M42 67 Q50 73 58 67" stroke="#c0522a" stroke-width="2" fill="none" stroke-linecap="round"/>
      <path d="M43.5 67.5 Q50 72 56.5 67.5" fill="#e8614a" opacity="0.7"/>
      <!-- Lip gloss -->
      <path d="M46 68 Q50 70 54 68" stroke="white" stroke-width="0.8" fill="none" opacity="0.5"/>

      <!-- Defs -->
      <defs>
        <radialGradient id="avatarGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%"   stop-color="#34d399" stop-opacity="0.4"/>
          <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0"/>
        </radialGradient>
        <linearGradient id="avatarBg" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%"   stop-color="#0f1e1a"/>
          <stop offset="100%" stop-color="#0d1020"/>
        </linearGradient>
        <linearGradient id="avatarRing" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%"   stop-color="#34d399"/>
          <stop offset="100%" stop-color="#8b5cf6"/>
        </linearGradient>
        <linearGradient id="outfitGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%"   stop-color="#1a0a3e"/>
          <stop offset="50%"  stop-color="#2d1060"/>
          <stop offset="100%" stop-color="#0d2010"/>
        </linearGradient>
      </defs>
    </svg>
  </div>
</template>

<script setup>
defineProps({
  size: {
    type: Number,
    default: 48,
  },
})
</script>

<style scoped>
.jessy-avatar {
  flex-shrink: 0;
  border-radius: 50%;
  overflow: hidden;
  display: block;
}
</style>
