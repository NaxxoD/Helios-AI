<template>
  <div class="auth-wrap">
    <div class="auth-card">
      <h1>Connexion</h1>
      <p class="error" v-if="error">
        {{ error }}
        <RouterLink v-if="nonVerifie" to="/auth/email-envoye" class="link-resend">Renvoyer le lien</RouterLink>
      </p>
      <form @submit.prevent="submit">
        <label>Email</label>
        <input v-model="email" type="email" required placeholder="vous@exemple.com" />
        <label>Mot de passe</label>
        <div class="pwd-row">
          <input v-model="password" :type="showPwd ? 'text' : 'password'" required placeholder="••••••••" />
          <button type="button" class="btn-eye" @click="showPwd = !showPwd" tabindex="-1" :title="showPwd ? 'Masquer' : 'Afficher'">
            <svg v-if="!showPwd" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" y1="2" x2="22" y2="22"/>
            </svg>
          </button>
        </div>
        <button type="submit" :disabled="loading">
          {{ loading ? 'Connexion...' : 'Se connecter' }}
        </button>
      </form>
      <p class="switch"><RouterLink to="/auth/mot-de-passe-oublie">Mot de passe oublié ?</RouterLink></p>
      <p class="switch">Pas encore de compte ? <RouterLink to="/inscription">S'inscrire</RouterLink></p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../../composables/useAuth.js'

const { connexion, user } = useAuth()
const router = useRouter()
const email    = ref('')
const password = ref('')
const showPwd  = ref(false)
const error      = ref('')
const loading    = ref(false)
const nonVerifie = ref(false)

async function submit() {
  error.value = ''
  nonVerifie.value = false
  loading.value = true
  try {
    await connexion(email.value, password.value)
    router.push(user.value?.is_admin ? '/admin/dashboard' : '/user/dashboard')
  } catch (e) {
    const status = e.response?.status
    error.value = e.response?.data?.detail ?? 'Erreur de connexion.'
    if (status === 403) nonVerifie.value = true
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-wrap { display: flex; justify-content: center; padding-top: 60px; }
.auth-card {
  background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-2xl);
  padding: 36px 40px; width: 100%; max-width: 400px;
}
h1 { font-size: var(--t-xl); color: var(--fg); margin-bottom: var(--s-6); }
form { display: flex; flex-direction: column; gap: var(--s-3); }
label { font-size: var(--t-sm); color: var(--fg-muted); }
input {
  background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--r-md);
  color: var(--fg-2); padding: 10px 12px; font-size: var(--t-md); width: 100%;
}
input:focus { outline: none; border-color: var(--accent); }
button[type="submit"] {
  margin-top: var(--s-2); background: var(--accent); color: #fff; border: none;
  border-radius: var(--r-md); padding: 12px; font-weight: var(--fw-bold); cursor: pointer; font-size: var(--t-md);
}
button[type="submit"]:disabled { opacity: .5; cursor: not-allowed; }
.error  { color: var(--danger); font-size: var(--t-sm); margin-bottom: var(--s-2); }
.switch { font-size: var(--t-sm); color: var(--fg-dim); margin-top: var(--s-5); text-align: center; }
.switch a { color: var(--accent); text-decoration: none; }
.link-resend { display: block; margin-top: 6px; color: var(--accent); font-size: var(--t-sm); text-decoration: none; }
.pwd-row { display: flex; gap: var(--s-2); }
.pwd-row input { flex: 1; }
.btn-eye {
  background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-md);
  padding: 0 12px; cursor: pointer; color: var(--fg-dim);
  display: flex; align-items: center; flex-shrink: 0;
  transition: border-color var(--t-fast), color var(--t-fast);
}
.btn-eye:hover { border-color: var(--accent); color: var(--fg-muted); }
</style>
