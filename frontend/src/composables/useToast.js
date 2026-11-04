import { ref } from 'vue';

// 화면 하단 알림. 앱 전체에서 하나의 상태를 공유합니다.
const message = ref('');
const visible = ref(false);
let timer = null;

export function toast(text) {
  message.value = text;
  visible.value = true;
  clearTimeout(timer);
  timer = setTimeout(() => { visible.value = false; }, 3200);
}

export function useToast() {
  return { message, visible, toast };
}
