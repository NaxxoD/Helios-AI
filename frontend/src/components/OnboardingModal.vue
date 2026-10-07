<template>
  <div class="overlay" @click.self="$emit('skip')">
    <div class="modal">
      <h2>Bienvenue sur Helios AI</h2>
      <p class="sub">Quel est ton profil d'utilisation des LLMs ?<br>On calibre ton seuil d'alerte CO₂ en conséquence.</p>

      <div class="profiles">
        <button
          v-for="p in profiles"
          :key="p.id"
          :class="['profile-btn', { selected: selected === p.id }]"
          @click="selected = p.id"
        >
          <span class="profile-label">{{ p.label }}</span>
          <span class="profile-desc">{{ p.desc }}</span>
          <span class="profile-seuil">Seuil suggéré : <strong>{{ p.seuil }} g CO₂/sem.</strong></span>
        </button>
      </div>

      <div class="actions">
        <button class="btn-primary" :disabled="!selected || saving" @click="confirm">
          {{ saving ? 'Enregistrement…' : 'Confirmer' }}
        </button>
        <button class="btn-skip" @click="$emit('skip')">Passer, je le définirai moi-même</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../api/index.js'

const emit = defineEmits(['done', 'skip'])

const selected = ref(null)
const saving   = ref(false)

const profiles = [
  { id: 'light',  label: 'Occasionnel',   desc: '2-3 sessions courtes par semaine',        seuil: 5   },
  { id: 'regular',label: 'Régulier',      desc: 'Une session par jour, usage varié',        seuil: 50  },
  { id: 'pro',    label: 'Professionnel', desc: 'Plusieurs sessions intenses par jour',     seuil: 150 },
  { id: 'heavy',  label: 'Heavy user',    desc: 'Usage massif, travail quasi-exclusif en IA', seuil: 300 },
]

async function confirm() {
  const profile = profiles.find(p => p.id === selected.value)
  if (!profile) return
  saving.value = true
  try {
    await api.patch('/settings', { co2_weekly_threshold: profile.seuil })
    emit('done', profile.seuil)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
  z-index: 100; padding: var(--s-5);
}
.modal {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--r-2xl); padding: var(--s-8); max-width: 520px; width: 100%;
}
.modal h2 { font-size: var(--t-xl); color: var(--fg); margin-bottom: var(--s-2); }
.sub { font-size: var(--t-sm); color: var(--fg-dim); margin-bottom: var(--s-6); line-height: var(--lh-normal); }

.profiles { display: flex; flex-direction: column; gap: var(--s-3); margin-bottom: var(--s-6); }
.profile-btn {
  display: flex; flex-direction: column; gap: 4px; text-align: left;
  background: var(--bg-base); border: 2px solid var(--border);
  border-radius: var(--r-lg); padding: var(--s-4) var(--s-5); cursor: pointer;
  transition: border-color var(--t-fast), background var(--t-fast);
}
.profile-btn:hover { border-color: var(--accent); }
.profile-btn.selected { border-color: var(--accent); background: var(--accent-soft); }
.profile-label { font-size: var(--t-md); font-weight: var(--fw-semibold); color: var(--fg); }
.profile-desc  { font-size: var(--t-sm); color: var(--fg-dim); }
.profile-seuil { font-size: var(--t-xs); color: var(--fg-dim); margin-top: 2px; }
.profile-seuil strong { color: var(--accent); }

.actions { display: flex; flex-direction: column; gap: var(--s-3); }
.btn-primary {
  background: var(--accent); color: #fff; border: none; border-radius: var(--r-md);
  padding: 11px; font-weight: var(--fw-semibold); cursor: pointer; font-size: var(--t-base);
}
.btn-primary:disabled { opacity: .45; cursor: not-allowed; }
.btn-skip {
  background: none; border: none; color: var(--fg-dim); font-size: var(--t-sm);
  cursor: pointer; text-align: center; text-decoration: underline;
}
.btn-skip:hover { color: var(--fg-muted); }
</style>
