import { useRouter } from 'vue-router';
import { ApiError } from '@/api/client';
import { useAuthStore } from '@/stores/auth';
import { loginRoute } from '@/utils';

// 로그인이 필요한 요청: 토큰이 만료되었으면(401) 로그아웃하고 로그인 페이지로 보냅니다.
// next를 주지 않으면 지금 화면으로 돌아옵니다.
export function useAuthedApi() {
  const auth = useAuthStore();
  const router = useRouter();

  return async function authed(path, options = {}, next) {
    try {
      return await auth.api(path, options);
    } catch (err) {
      if (err.status === 401) {
        auth.logout();
        router.push(loginRoute(next ?? router.currentRoute.value.fullPath));
        throw new ApiError('로그인이 필요합니다.', 401);
      }
      throw err;
    }
  };
}
