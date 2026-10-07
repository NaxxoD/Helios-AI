<template>
  <div class="auth-wrap">
    <div class="auth-card">
      <div class="icon">✉️</div>
      <h1>Vérifiez votre boîte mail</h1>
      <p class="info">Un email de confirmation a été envoyé. Cliquez sur le lien pour activer votre compte.</p>
      <div class="resend">
        <p>Vous n'avez pas reçu l'email ?</p>
        <form @submit.prevent="resend">
          <input v-model="email" type="email" required placeholder="votre@email.com" />
          <button type="submit" :disabled="loading">{{ loading ? 'Envoi...' : 'Renvoyer le lien' }}</button>
        </form>
        <p class="feedback" v-if="feedback">{{ feedback }}</p>
      </div>
      <p class="switch">Déjà vérifié ? <RouterLink to="/connexion">Se connecter</RouterLink></p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../../api/index.js'

const email    = ref('')
const loading  = ref(false)
const feedback = ref('')

async function resend() {
  loading.value = true
  feedback.value = ''
  try {
    await api.post('/auth/resend-verification', { email: email.value })
    feedback.value = 'Email renvoyé si le compte existe et n\'est pas encore vérifié.'
  } catch {
    feedback.value = 'Une erreur est survenue.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-wrap { display: flex; justify-content: center; padding-top: 60px; }
.auth-card {
  background: #1e2330; border: 1px solid #2d3748; border-radius: 12px;
  padding: 36px 40px; width: 100%; max-width: 400px; text-align: center;
}
.icon { font-size: 2.5rem; margin-bottom: 16px; }
h1 { font-size: 1.4rem; color: #f8fafc; margin-bottom: 12px; }
.info { color: #94a3b8; font-size: 0.9rem; line-height: 1.6; margin-bottom: 24px; }
.resend { border-top: 1px solid #2d3748; padding-top: 20px; }
.resend p { font-size: 0.85rem; color: #64748b; margin-bottom: 10px; }
.resend form { display: flex; flex-direction: column; gap: 8px; }
.resend input {
  background: #0f1117; border: 1px solid #2d3748; border-radius: 6px;
  color: #e2e8f0; padding: 10px 12px; font-size: 0.9rem; width: 100%;
}
.resend button {
  background: #334155; color: #e2e8f0; border: none;
  border-radius: 6px; padding: 10px; font-size: 0.88rem; cursor: pointer;
}
.resend button:disabled { opacity: .5; cursor: not-allowed; }
.feedback { font-size: 0.82rem; color: #22c55e; margin-top: 8px; }
.switch { font-size: 0.85rem; color: #64748b; margin-top: 20px; }
.switch a { color: #3b82f6; text-decoration: none; }
</style>
