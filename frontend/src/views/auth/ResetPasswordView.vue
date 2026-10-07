<template>
  <div class="auth-wrap">
    <div class="auth-card">
      <template v-if="!done">
        <h1>Nouveau mot de passe</h1>
        <p class="error" v-if="error">{{ error }}</p>
        <form @submit.prevent="submit">
          <label>Nouveau mot de passe</label>
          <input v-model="password" type="password" required placeholder="••••••••" />
          <label>Confirmer</label>
          <input v-model="confirm" type="password" required placeholder="••••••••" />
          <button type="submit" :disabled="loading">
            {{ loading ? 'Enregistrement...' : 'Enregistrer' }}
          </button>
        </form>
      </template>
      <template v-else>
        <div class="icon">✅</div>
        <h1>Mot de passe mis à jour</h1>
        <p class="info">Vous pouvez maintenant vous connecter avec votre nouveau mot de passe.</p>
        <RouterLink to="/connexion" class="btn">Se connecter</RouterLink>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../api/index.js'

const route    = useRoute()
const password = ref('')
const confirm  = ref('')
const error    = ref('')
const loading  = ref(false)
const done     = ref(false)

async function submit() {
  if (password.value !== confirm.value) {
    error.value = 'Les mots de passe ne correspondent pas.'
    return
  }
  error.value = ''
  loading.value = true
  try {
    await api.post('/auth/reset-password', { token: route.params.token, new_password: password.value })
    done.value = true
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Lien invalide ou expiré.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-wrap { display: flex; justify-content: center; padding-top: 60px; }
.auth-card {
  background: #1e2330; border: 1px solid #2d3748; border-radius: 12px;
  padding: 36px 40px; width: 100%; max-width: 400px;
}
.icon { font-size: 2.5rem; text-align: center; margin-bottom: 16px; }
h1 { font-size: 1.5rem; color: #f8fafc; margin-bottom: 24px; }
.info { color: #94a3b8; font-size: 0.9rem; line-height: 1.6; margin-bottom: 24px; }
form { display: flex; flex-direction: column; gap: 12px; }
label { font-size: 0.82rem; color: #94a3b8; }
input {
  background: #0f1117; border: 1px solid #2d3748; border-radius: 6px;
  color: #e2e8f0; padding: 10px 12px; font-size: 0.9rem; width: 100%;
}
button {
  margin-top: 8px; background: #3b82f6; color: #fff; border: none;
  border-radius: 6px; padding: 12px; font-weight: 700; cursor: pointer;
}
button:disabled { opacity: .5; cursor: not-allowed; }
.error { color: #ef4444; font-size: 0.85rem; margin-bottom: 8px; }
.btn {
  display: inline-block; padding: 12px 28px; background: #3b82f6;
  color: #fff; border-radius: 6px; text-decoration: none; font-weight: 700;
}
</style>
