'use strict';
// API 주소. nginx가 /api/ 요청을 백엔드로 프록시하므로 기본값은 같은 출처의 상대 경로입니다.
// 프록시 없이 직접 연결할 때만 예: 'http://localhost:8000/api/v1' 로 바꿉니다.
window.TIKIT_CONFIG = Object.freeze({
  apiBase: '/api/v1',
});
