import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { loginRoute, safeNext } from '@/utils';
import { toast } from '@/composables/useToast';
import HomeView from '@/views/HomeView.vue';

const routes = [
  { path: '/', name: 'home', component: HomeView, meta: { title: 'TIKIT 티킷 — 취향이 만나는 순간', footer: true } },
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { title: '로그인 — TIKIT 티킷', guestOnly: true } },
  { path: '/signup', name: 'signup', component: () => import('@/views/SignupView.vue'), meta: { title: '회원가입 — TIKIT 티킷', guestOnly: true } },
  { path: '/my-tickets', name: 'my-tickets', component: () => import('@/views/MyTicketsView.vue'), meta: { title: '마이티킷 — TIKIT 티킷', requiresAuth: true, footer: true } },
  { path: '/mypage/:section?', name: 'mypage', component: () => import('@/views/MyPageView.vue'), meta: { title: '마이페이지 — TIKIT 티킷', requiresAuth: true, footer: true } },

  // 이전(.html) 주소 호환
  { path: '/index.html', redirect: to => ({ path: '/', query: to.query }) },
  { path: '/login.html', redirect: to => ({ path: '/login', query: to.query }) },
  { path: '/signup.html', redirect: to => ({ path: '/signup', query: to.query }) },
  { path: '/mypage.html', redirect: to => ({ path: `/mypage/${to.hash.slice(1)}`, hash: '' }) },
  { path: '/:pathMatch(.*)*', redirect: '/' },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, saved) {
    if (saved) return saved;
    if (to.path === from.path) return false; // 같은 화면 안에서 쿼리만 바뀔 때는 스크롤 유지
    return { top: 0 };
  },
});

router.beforeEach(async to => {
  if (!to.meta.requiresAuth && !to.meta.guestOnly) return true;
  const auth = useAuthStore();
  let user = null;
  try {
    user = await auth.restore();
  } catch (err) {
    toast(err.message);
  }
  // 로그인하지 않았으면 로그인 페이지로 보냈다가 다시 돌아옵니다.
  if (to.meta.requiresAuth && !user) return loginRoute(to.fullPath);
  // 이미 로그인된 탭에서 로그인·회원가입 화면을 열면 바로 돌려보냅니다.
  if (to.meta.guestOnly && user) return safeNext(to.query.next);
  return true;
});

router.afterEach(to => {
  if (to.meta.title) document.title = to.meta.title;
});

export default router;
