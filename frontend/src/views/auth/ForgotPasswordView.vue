<template>
  <div class="auth-wrap">
    <div class="auth-card">
      <h1>Mot de passe oublié</h1>
      <template v-if="!sent">
        <p class="info">Entrez votre adresse email, vous recevrez un lien de réinitialisation.</p>
        <p class="error" v-if="error">{{ error }}</p>
        <form @submit.prevent="submit">
          <label>Email</label>
          <input v-model="email" type="email" required placeholder="vous@exemple.com" />
          <button type="submit" :disabled="loading">
            {{ loading ? 'Envoi...' : 'Envoyer le lien' }}
          </button>
        </form>
      </template>
      <template v-else>
        <div class="icon">✉️</div>
        <p class="info">Si cet email existe, un lien de réinitialisation a été envoyé.</p>
      </template>
      <p class="switch"><RouterLink to="/connexion">Retour à la connexion</RouterLink></p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../../api/index.js'

const email   = ref('')
const error   = ref('')
const loading = ref(false)
const sent    = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await api.post('/auth/forgot-password', { email: email.value })
    sent.value = true
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Une erreur est survenue.'
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
h1 { font-size: 1.5rem; color: #f8fafc; margin-bottom: 12px; }
.info { color: #94a3b8; font-size: 0.88rem; line-height: 1.6; margin-bottom: 16px; }
.icon { font-size: 2.5rem; text-align: center; margin: 16px 0; }
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
.switch { font-size: 0.85rem; color: #64748b; margin-top: 20px; text-align: center; }
.switch a { color: #3b82f6; text-decoration: none; }
</style>
