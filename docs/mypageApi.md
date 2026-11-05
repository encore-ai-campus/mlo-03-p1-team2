# 마이페이지

마이페이지의 예매, 찜, 리포트, 알림 설정, 탈퇴는 로그인한 계정을 기준으로 동작한다.
공연 하트는 기존 `/api/v1/favorites`에 저장되며 홈과 찜 패널이 같은 Pinia 상태를 사용한다.
찜 해제 시 목록에서 제거되고 새로고침해도 서버 저장 상태를 불러온다.

## API

아래 경로 앞에는 `/api/v1`을 붙인다. 모두 Bearer 인증이 필요하다.
상세 입력·응답 계약은 FastAPI `/openapi.json`의 `mypage` 태그와
`backend/app/schemas/mypage.py`에서 확인할 수 있다.

| 요청 | 동작 |
| --- | --- |
| `GET /users/me/taste-report` | 현재 MBTI, 개인 장르별 조회·현재 찜·완료 예매 수, 같은 MBTI 다른 관객의 찜 집계 |
| `GET /users/me/notification-settings` | 계정별 알림 설정. 미저장 상태에서는 두 설정 모두 꺼짐 |
| `PUT /users/me/notification-settings` | `booking_reminders`, `favorite_updates` 두 Boolean 저장 |
| `GET /users/me/notifications` | 저장된 설정에 맞는 예정 관람 및 찜 공연 소식 목록 |
| `DELETE /users/me` | 기존 탈퇴 API. 알림 설정도 함께 삭제 |

리포트는 취소·결제 대기 예매를 제외한다. 이전 모의 결제 내역은 완료 예매에 포함한다.
관심 비율은 조회 횟수, 현재 찜 개수, 완료 예매 건수의 합으로 계산한다.
같은 MBTI 집계는 본인을 제외하고 현재 찜 기록이 있는 계정만 포함하며 개인 정보는 반환하지 않는다.

알림은 마이페이지 안에서 조회하는 목록이다. 한국 시간으로 오늘부터 7일 이내의
결제 완료 공연, 진행 중이거나 7일 이내 시작하는 찜 공연을 표시한다.
메일·문자·브라우저 푸시는 발송하지 않는다.

## DB 적용

기존 DB 버전 `0002`에서 `0003`으로 올리면 `notification_settings` 테이블이 추가된다.
공유 DB 적용은 승인을 받은 뒤 실행한다. 기존 데이터는 수정하지 않는다.

MySQL/MariaDB에서는 기존 `users.id`의 문자셋·콜레이션을 읽어 새 테이블에도 적용한다.
DB 기본 콜레이션이 변경되어도 외래 키 양쪽 컬럼이 달라지지 않게 하기 위함이다.
`0003` 적용 중 외래 키 오류(`errno: 150`)가 발생한 환경은 수정된 마이그레이션으로
`python -m alembic upgrade head`를 다시 실행한다. 기존 `users` 테이블이나 DB 기본값을 변경하지 않는다.
이 호환 처리는 온라인 마이그레이션에서 적용된다. `--sql` 출력만으로는 기존 DB 메타데이터를 확인하지 않는다.

```powershell
cd backend
python -m alembic upgrade head
```

## 검증

```powershell
cd backend
python -m pytest -q
cd ../frontend
npm test
npm run build
```

`backend/tests/mypage.postman_collection.json`은 가입부터 찜·리포트·설정 저장·탈퇴까지
검증하는 로컬 Postman 컬렉션이다. 일회용 계정을 생성·삭제하므로 격리된 테스트 API에서 실행한다.

```powershell
postman collection run backend/tests/mypage.postman_collection.json --env-var baseUrl=http://127.0.0.1:18001/api/v1 --no-report-events
```

새 마이그레이션 `0002 → 0003`의 적용·되돌리기·재적용은 격리 SQLite에서 검증했다.
기존 `0002`의 외래키 ALTER는 SQLite에서 지원하지 않으므로 SQLite 신규 구축 시에는
테스트처럼 SQLAlchemy 메타데이터로 기존 스키마를 구성해야 한다. 서비스 DB는 MySQL이다.
