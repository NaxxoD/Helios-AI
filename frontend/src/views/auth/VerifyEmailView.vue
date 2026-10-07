<template>
  <div class="auth-wrap">
    <div class="auth-card">
      <div v-if="loading" class="icon">⏳</div>
      <div v-else-if="success" class="icon">✅</div>
      <div v-else class="icon">❌</div>
      <h1>{{ title }}</h1>
      <p class="info">{{ message }}</p>
      <RouterLink v-if="success" to="/user/dashboard" class="btn">Accéder à mon espace</RouterLink>
      <RouterLink v-else-if="!loading" to="/connexion" class="btn">Retour à la connexion</RouterLink>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../api/index.js'
import { useAuth } from '../../composables/useAuth.js'

const route   = useRoute()
const { setToken } = useAuth()
const loading = ref(true)
const success = ref(false)
const title   = ref('Vérification en cours...')
const message = ref('')

onMounted(async () => {
  try {
    const { data } = await api.get(`/auth/verify/${route.params.token}`)
    setToken(data.access_token, { id: data.id, email: data.email, is_admin: data.is_admin })
    success.value = true
    title.value   = 'Compte activé !'
    message.value = 'Votre adresse email a été confirmée. Bienvenue sur Helios AI.'
  } catch (e) {
    title.value   = 'Lien invalide'
    message.value = e.response?.data?.detail ?? 'Ce lien est invalide ou a déjà été utilisé.'
  } finally {
    loading.value = false
  }
})
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
.btn {
  display: inline-block; padding: 12px 28px; background: #3b82f6;
  color: #fff; border-radius: 6px; text-decoration: none; font-weight: 700;
}
</style>
