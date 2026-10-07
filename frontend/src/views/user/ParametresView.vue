<template>
  <div>
    <div class="page-header">
      <h1>Paramètres</h1>
    </div>

    <!-- Seuil CO₂ -->
    <div class="section-card">
      <h2>Seuil d'alerte CO₂ hebdomadaire</h2>
      <p class="section-desc">
        Une bannière s'affiche sur ton dashboard quand ta consommation CO₂ des 7 derniers jours
        dépasse ce seuil. Laisse vide pour désactiver.
      </p>
      <div class="threshold-row">
        <input type="number" v-model.number="threshold" step="0.001" min="0"
               placeholder="ex : 50" class="threshold-input" />
        <span class="unit">g CO₂ / semaine</span>
        <button class="btn-save" :disabled="thresholdStatus === 'saving'" @click="saveThreshold">
          {{ thresholdStatus === 'saving' ? 'Enregistrement…' : 'Enregistrer' }}
        </button>
      </div>
      <p v-if="thresholdStatus === 'saved'" class="msg-ok">Seuil mis à jour.</p>
      <p v-if="thresholdStatus === 'error'" class="msg-err">Erreur lors de la sauvegarde.</p>
    </div>

    <!-- Mon compte -->
    <div class="section-card">
      <h2>Mon compte</h2>
      <div class="info-row"><span>Email</span><strong>{{ user?.email }}</strong></div>
      <div class="info-row">
        <span>Rôle</span>
        <span :class="['badge', user?.is_admin ? 'admin' : 'user']">
          {{ user?.is_admin ? 'Administrateur' : 'Utilisateur' }}
        </span>
      </div>
    </div>

    <!-- Changer mot de passe -->
    <div class="section-card">
      <h2>Changer le mot de passe</h2>
      <p class="section-desc">Minimum 8 caractères.</p>
      <form @submit.prevent="changePassword" class="pwd-form">
        <div class="field">
          <label>Mot de passe actuel</label>
          <div class="pwd-input-row">
            <input :type="showPwd ? 'text' : 'password'" v-model="currentPwd" required />
            <button type="button" class="btn-eye" @click="showPwd = !showPwd">
              {{ showPwd ? '🙈' : '👁' }}
            </button>
          </div>
        </div>
        <div class="field">
          <label>Nouveau mot de passe</label>
          <input :type="showPwd ? 'text' : 'password'" v-model="newPwd" required />
        </div>
        <div class="field">
          <label>Confirmer</label>
          <input :type="showPwd ? 'text' : 'password'" v-model="confirmPwd" required />
        </div>
        <p v-if="pwdError" class="msg-err">{{ pwdError }}</p>
        <p v-if="pwdStatus === 'saved'" class="msg-ok">Mot de passe mis à jour.</p>
        <button type="submit" class="btn-save" :disabled="pwdStatus === 'saving'">
          {{ pwdStatus === 'saving' ? 'Mise à jour…' : 'Mettre à jour' }}
        </button>
      </form>
    </div>

    <!-- Zone de danger -->
    <div class="section-card danger-card">
      <h2 class="danger-title">Zone de danger</h2>
      <p class="section-desc">
        La suppression est définitive et irréversible. Toutes tes sessions et données seront effacées.
      </p>
      <div class="field">
        <label>Tape <strong>SUPPRIMER</strong> pour confirmer</label>
        <input v-model="deleteConfirm" placeholder="SUPPRIMER" class="danger-input" />
      </div>
      <button class="btn-danger"
        :disabled="deleteConfirm !== 'SUPPRIMER' || deleteLoading"
        @click="deleteAccount">
        {{ deleteLoading ? 'Suppression…' : 'Supprimer mon compte' }}
      </button>
      <p v-if="deleteError" class="msg-err">{{ deleteError }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/index.js'
import { useAuth } from '../../composables/useAuth.js'

const router = useRouter()
const { deconnexion } = useAuth()

const user            = ref(null)
const threshold       = ref(null)
const thresholdStatus = ref('idle')

const currentPwd  = ref('')
const newPwd      = ref('')
const confirmPwd  = ref('')
const showPwd     = ref(false)
const pwdStatus   = ref('idle')
const pwdError    = ref('')

const deleteConfirm = ref('')
const deleteLoading = ref(false)
const deleteError   = ref('')

onMounted(async () => {
  const { data } = await api.get('/user/dashboard')
  user.value      = data.user
  threshold.value = data.user.threshold
})

async function saveThreshold() {
  thresholdStatus.value = 'saving'
  try {
    await api.patch('/settings', { co2_weekly_threshold: threshold.value || null })
    thresholdStatus.value = 'saved'
    setTimeout(() => { thresholdStatus.value = 'idle' }, 2500)
  } catch {
    thresholdStatus.value = 'error'
  }
}

async function changePassword() {
  pwdError.value  = ''
  pwdStatus.value = 'idle'
  if (newPwd.value !== confirmPwd.value) {
    pwdError.value = 'Les mots de passe ne correspondent pas.'
    return
  }
  pwdStatus.value = 'saving'
  try {
    await api.patch('/auth/password', {
      current_password: currentPwd.value,
      new_password:     newPwd.value,
    })
    currentPwd.value = ''
    newPwd.value     = ''
    confirmPwd.value = ''
    pwdStatus.value  = 'saved'
    setTimeout(() => { pwdStatus.value = 'idle' }, 2500)
  } catch (e) {
    pwdError.value  = e.response?.data?.detail ?? 'Erreur.'
    pwdStatus.value = 'idle'
  }
}

async function deleteAccount() {
  deleteLoading.value = true
  deleteError.value   = ''
  try {
    await api.delete('/auth/account')
    deconnexion()
    router.push('/')
  } catch {
    deleteLoading.value = false
    deleteError.value   = 'Erreur lors de la suppression. Réessayez ou contactez le support.'
  }
}
</script>

<style scoped>
.page-header { margin-bottom: var(--s-8); }
.page-header h1 { font-size: var(--t-2xl); color: var(--fg); }

.section-card {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--r-2xl); padding: var(--s-8); max-width: 560px; margin-bottom: var(--s-6);
}
.section-card h2 { font-size: var(--t-lg); color: var(--fg); margin-bottom: var(--s-3); }
.section-desc { font-size: var(--t-sm); color: var(--fg-dim); margin-bottom: var(--s-5); line-height: var(--lh-normal); }

/* Threshold */
.threshold-row { display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap; }
.threshold-input {
  background: var(--bg-input); border: 1px solid var(--border); color: var(--fg-2);
  padding: 9px 12px; border-radius: var(--r-md); font-size: var(--t-base); width: 120px;
}
.unit { font-size: var(--t-sm); color: var(--fg-dim); }

/* Compte */
.info-row { display: flex; justify-content: space-between; align-items: center; padding: var(--s-3) 0; border-bottom: 1px solid var(--border-subtle); font-size: var(--t-base); }
.info-row:last-child { border-bottom: none; }
.info-row span:first-child { color: var(--fg-dim); }
.info-row strong { color: var(--fg); }
.badge { padding: 3px 10px; border-radius: var(--r-pill); font-size: var(--t-xs); font-weight: var(--fw-semibold); }
.badge.admin { background: var(--co2-avoided-soft); color: var(--co2-avoided); }
.badge.user  { background: var(--accent-soft);      color: var(--accent); }

/* Password */
.pwd-form { display: flex; flex-direction: column; gap: var(--s-4); }
.field { display: flex; flex-direction: column; gap: var(--s-2); }
.field label { font-size: var(--t-sm); color: var(--fg-muted); }
.field input {
  background: var(--bg-input); border: 1px solid var(--border); color: var(--fg-2);
  padding: 9px 12px; border-radius: var(--r-md); font-size: var(--t-base); width: 100%;
}
.pwd-input-row { display: flex; gap: var(--s-2); }
.pwd-input-row input { flex: 1; }
.btn-eye { background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-md); padding: 0 10px; cursor: pointer; font-size: var(--t-base); }

/* Boutons */
.btn-save {
  background: var(--accent); color: #fff; border: none; border-radius: var(--r-md);
  padding: 9px 20px; font-weight: var(--fw-semibold); cursor: pointer; font-size: var(--t-base);
}
.btn-save:disabled { opacity: .5; cursor: not-allowed; }

.msg-ok  { font-size: var(--t-sm); color: var(--ok);     margin-top: var(--s-2); }
.msg-err { font-size: var(--t-sm); color: var(--danger);  margin-top: var(--s-2); }

/* Danger */
.danger-card  { border-color: var(--danger); }
.danger-title { color: var(--danger) !important; }
.danger-input {
  background: var(--bg-input); border: 1px solid var(--danger); color: var(--fg-2);
  padding: 9px 12px; border-radius: var(--r-md); font-size: var(--t-base); width: 100%;
}
.btn-danger {
  background: var(--danger); color: #fff; border: none; border-radius: var(--r-md);
  padding: 9px 20px; font-weight: var(--fw-semibold); cursor: pointer; font-size: var(--t-base);
  margin-top: var(--s-4);
}
.btn-danger:disabled { opacity: .4; cursor: not-allowed; }
</style>
