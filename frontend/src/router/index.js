import { createRouter, createWebHistory } from 'vue-router'
import AccueilView        from '../views/AccueilView.vue'
import UploadView         from '../views/UploadView.vue'
import ManuelView         from '../views/ManuelView.vue'
import ConnexionView      from '../views/auth/ConnexionView.vue'
import InscriptionView    from '../views/auth/InscriptionView.vue'
import EmailEnvoyeView    from '../views/auth/EmailEnvoyeView.vue'
import VerifyEmailView    from '../views/auth/VerifyEmailView.vue'
import ForgotPasswordView from '../views/auth/ForgotPasswordView.vue'
import ResetPasswordView  from '../views/auth/ResetPasswordView.vue'
import UserDashboard      from '../views/user/DashboardView.vue'
import SessionDetail      from '../views/user/SessionDetailView.vue'
import ConversationDetail from '../views/user/ConversationDetailView.vue'
import HistoriqueView     from '../views/user/HistoriqueView.vue'
import OptimiseurView     from '../views/user/OptimiseurView.vue'
import ParametresView     from '../views/user/ParametresView.vue'
import AdminDashboard     from '../views/admin/DashboardView.vue'
import ExtensionView      from '../views/ExtensionView.vue'
import ChatView           from '../views/user/ChatView.vue'
import NotFoundView       from '../views/NotFoundView.vue'
import PitchView          from '../views/PitchView.vue'
import DemoView           from '../views/user/DemoView.vue'

const routes = [
  { path: '/',                            component: AccueilView },
  { path: '/upload',                      component: UploadView,  meta: { requiresAuth: true } },
  { path: '/manuel',                      component: ManuelView,  meta: { requiresAuth: true } },
  { path: '/connexion',                   component: ConnexionView },
  { path: '/inscription',                 component: InscriptionView },
  { path: '/auth/email-envoye',           component: EmailEnvoyeView },
  { path: '/auth/verify/:token',          component: VerifyEmailView },
  { path: '/auth/mot-de-passe-oublie',    component: ForgotPasswordView },
  { path: '/auth/reset-password/:token',  component: ResetPasswordView },
  { path: '/user/dashboard',      component: UserDashboard,  meta: { requiresAuth: true } },
  { path: '/user/sessions/:id',   component: SessionDetail,  meta: { requiresAuth: true } },
  { path: '/user/conversations/:uuid', component: ConversationDetail, meta: { requiresAuth: true } },
  { path: '/historique',          component: HistoriqueView, meta: { requiresAuth: true } },
  { path: '/optimiseur',          component: OptimiseurView, meta: { requiresAuth: true } },
  { path: '/parametres',          component: ParametresView, meta: { requiresAuth: true } },
  { path: '/admin/dashboard',     component: AdminDashboard, meta: { requiresAdmin: true } },
  { path: '/extension',           component: ExtensionView,  meta: { requiresAuth: true } },
  { path: '/chat',               component: ChatView },
  { path: '/chat/:uuid',         component: ChatView, meta: { requiresAuth: true } },
  { path: '/pitch',              component: PitchView },
  { path: '/demo',               component: DemoView },
  { path: '/:pathMatch(.*)*',    component: NotFoundView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  const user  = JSON.parse(localStorage.getItem('user') || 'null')

  if ((to.meta.requiresAuth || to.meta.requiresAdmin) && !token) {
    next('/connexion')
  } else if (to.meta.requiresAdmin && !user?.is_admin) {
    next('/user/dashboard')
  } else {
    next()
  }
})

export default router
