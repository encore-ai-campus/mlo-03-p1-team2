import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { useAuthedApi } from '@/composables/useAuthedApi';
import { toast } from '@/composables/useToast';

// 화면을 연 뒤 권한이 회수되어도 서버의 403 응답을 기준으로 관리자 화면을 벗어납니다.
export function useAdminApi() {
  const authed = useAuthedApi();
  const auth = useAuthStore();
  const router = useRouter();
  return async (path, options = {}) => {
    try {
      return await authed(path, options);
    } catch (err) {
      if (err.status === 403) {
        if (auth.profile) auth.profile.is_admin = false;
        toast(err.message);
        router.replace('/');
      }
      throw err;
    }
  };
}
