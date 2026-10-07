import { ref, computed } from 'vue'
import api from '../api/index.js'

const token    = ref(localStorage.getItem('token'))
const userData = ref(JSON.parse(localStorage.getItem('user') || 'null'))

export function useAuth() {
  const isAuthenticated = computed(() => !!token.value)
  const isAdmin         = computed(() => !!userData.value?.is_admin)

  async function inscription(email, password) {
    const { data } = await api.post('/auth/inscription', { email, password })
    if (data.access_token) {
      token.value = data.access_token
      localStorage.setItem('token', data.access_token)
      userData.value = { id: data.id, email: data.email, is_admin: data.is_admin }
      localStorage.setItem('user', JSON.stringify(userData.value))
      return data.access_token
    }
    return null
  }

  async function connexion(email, password) {
    const { data } = await api.post('/auth/connexion', { email, password })
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)
    userData.value = { id: data.id, email: data.email, is_admin: data.is_admin }
    localStorage.setItem('user', JSON.stringify(userData.value))
  }

  function setToken(accessToken, user = null) {
    token.value = accessToken
    localStorage.setItem('token', accessToken)
    if (user) {
      userData.value = user
      localStorage.setItem('user', JSON.stringify(user))
    }
  }

  function deconnexion() {
    token.value    = null
    userData.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    api.post('/auth/logout').catch(() => {})
  }

  return { token, user: userData, isAuthenticated, isAdmin, inscription, connexion, deconnexion, setToken }
}
