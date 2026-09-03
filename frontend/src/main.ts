import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import vuetify from './plugins/vuetify'
import './plugins/m3e'
import { router } from './router'
import './style.css'

const app = createApp(App)

const pinia = createPinia()
app.use(pinia)
if ((import.meta as any).env?.DEV) {
  ;(window as any).$pinia = pinia
}
app.use(router)
app.use(vuetify)

app.mount('#app')
