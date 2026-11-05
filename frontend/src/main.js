import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import { useAuthStore } from './stores/auth';
import { installTracking } from './utils/tracker';
import './assets/styles.css';

const pinia = createPinia();
// 사용자 행동 이벤트 수집 (큐 10개 또는 3초마다 백엔드로 전송 → MongoDB)
installTracking({ router, getToken: () => useAuthStore(pinia).token });
createApp(App).use(pinia).use(router).mount('#app');
