<template>
  <div class="ext-page">
    <div class="hero">
      <h1>Extension Chrome</h1>
      <p class="hero-sub">Trackez vos tokens en temps réel sur ChatGPT, Claude.ai et Gemini.</p>
    </div>

    <div class="steps-grid">
      <div class="step-card" v-for="(step, i) in steps" :key="i">
        <div class="step-num">{{ i + 1 }}</div>
        <div class="step-body">
          <h3>{{ step.title }}</h3>
          <p>{{ step.desc }}</p>
          <code v-if="step.code">{{ step.code }}</code>
        </div>
      </div>
    </div>

    <div class="platforms-section">
      <h2>Plateformes supportées</h2>
      <div class="platforms">
        <span class="badge" v-for="p in platforms" :key="p">{{ p }}</span>
      </div>
    </div>

    <div class="note-card">
      <span class="note-icon">💡</span>
      <p>Connectez-vous sur Helios AI avant de cliquer <strong>Sauvegarder</strong> dans l'overlay pour que la session soit enregistrée dans votre espace.</p>
    </div>
  </div>
</template>

<script setup>
const steps = [
  {
    title: 'Téléchargez le dossier extension',
    desc: "Récupérez le dossier chrome-extension/ depuis le dépôt du projet.",
    code: 'chrome-extension/',
  },
  {
    title: 'Chargez l\'extension dans Chrome',
    desc: "Allez sur chrome://extensions → activez le mode développeur (en haut à droite) → cliquez Charger l'extension non empaquetée → sélectionnez le dossier chrome-extension/.",
    code: 'chrome://extensions',
  },
  {
    title: 'Utilisez l\'overlay',
    desc: "Ouvrez ChatGPT, Claude.ai ou Gemini. L'overlay apparaît automatiquement en bas à droite et compte vos tokens en temps réel. Cliquez Sauvegarder pour enregistrer la session.",
    code: null,
  },
]

const platforms = ['ChatGPT', 'Claude.ai', 'Gemini']
</script>

<style scoped>
.ext-page { max-width: 720px; }

.hero { margin-bottom: var(--s-10); }
.hero h1 { font-size: var(--t-2xl); color: var(--fg); margin-bottom: var(--s-2); }
.hero-sub { color: var(--fg-dim); font-size: var(--t-md); line-height: 1.6; }

.steps-grid { display: flex; flex-direction: column; gap: var(--s-4); margin-bottom: var(--s-10); }

.step-card {
  display: flex; gap: var(--s-5); align-items: flex-start;
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--r-xl); padding: var(--s-5) var(--s-6);
}
.step-num {
  width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0;
  background: var(--accent); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-weight: var(--fw-bold); font-size: var(--t-base);
}
.step-body h3 { font-size: var(--t-md); color: var(--fg); margin-bottom: var(--s-2); }
.step-body p  { font-size: var(--t-sm); color: var(--fg-dim); line-height: 1.6; }
.step-body code {
  display: inline-block; margin-top: var(--s-2);
  background: var(--bg-base); border: 1px solid var(--border);
  border-radius: var(--r-sm); padding: 3px 10px;
  font-family: var(--font-mono); font-size: var(--t-sm); color: var(--accent);
}

.platforms-section { margin-bottom: var(--s-8); }
.platforms-section h2 { font-size: var(--t-lg); color: var(--fg-muted); margin-bottom: var(--s-4); }
.platforms { display: flex; gap: var(--s-3); flex-wrap: wrap; }
.badge {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--r-pill); padding: 6px 16px;
  font-size: var(--t-sm); color: var(--fg); font-weight: var(--fw-semibold);
}

.note-card {
  display: flex; gap: var(--s-4); align-items: flex-start;
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--r-xl); padding: var(--s-5) var(--s-6);
}
.note-icon { font-size: 1.4rem; flex-shrink: 0; }
.note-card p { font-size: var(--t-sm); color: var(--fg-dim); line-height: 1.6; }
.note-card strong { color: var(--fg); }
</style>
