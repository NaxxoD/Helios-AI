import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index.js'
import './assets/main.css'
import './assets/tokens.css'

createApp(App).use(router).mount('#app')
