import { useAuthedApi } from '@/composables/useAuthedApi';
import { track } from '@/utils/tracker';

// 성공한 예매 응답으로 행동 이벤트를 남기고 응답을 그대로 돌려줍니다.
const tracked = type => order => {
  track(type, {
    reservation_id: order.id, performance_id: order.performance_id, category: order.category,
    seat_grade: order.seat_grade, quantity: order.quantity, amount_krw: order.amount,
  });
  return order;
};

// 예매 API 모음. 로그인 만료(401)는 useAuthedApi가 로그인 화면으로 보내 처리합니다.
// next: 로그인 후 돌아올 주소 (생략하면 지금 화면)
export function useReservations() {
  const authed = useAuthedApi();

  return {
    // 내 예매 목록 (결제 정보 포함, 최신순)
    list: next => authed('/reservations', {}, next),

    // 예매 요청 → 서버가 예매(REQUESTED) + 결제 대기(PENDING)를 만듭니다.
    create: ({ show, date, slot, premium, quantity, requestKey }, next) => authed('/reservations', {
      method: 'POST',
      body: {
        performance_id: show.id, performance_date: date, session_time: slot,
        seat_grade: premium ? 'PREMIUM' : 'STANDARD', quantity, request_key: requestKey,
      },
    }, next).then(tracked('reservation_request')),

    // 모의 결제 완료 → 예매 확정 (CONFIRMED / COMPLETED)
    complete: (id, next) => authed(`/reservations/${encodeURIComponent(id)}/complete`, { method: 'POST' }, next)
      .then(tracked('payment_complete')),

    // 예매·결제 동시 취소 (CANCELLED / CANCELLED)
    cancel: (id, next) => authed(`/reservations/${encodeURIComponent(id)}/cancel`, { method: 'POST' }, next)
      .then(tracked('reservation_cancel')),
  };
}
