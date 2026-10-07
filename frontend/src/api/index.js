import axios from 'axios'
import router from '../router'

const api = axios.create({ baseURL: '/api', withCredentials: true })

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(null, err => {
  if (err.response?.status === 401) {
    const url = err.config?.url ?? ''
    if (url.includes('/chat/send')) {
      // Session expirée en cours de conversation — laisser remonter au chat
      return Promise.reject(err)
    }
    localStorage.removeItem('token')
    router.push('/connexion')
  }
  return Promise.reject(err)
})

export default api
