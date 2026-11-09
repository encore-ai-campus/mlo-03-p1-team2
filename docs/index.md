# 문서 안내

각 항목의 상세 내용은 아래 기준 문서에서 관리하고 다른 문서는 링크로 참조한다.

| 목적 | 기준 문서 |
| --- | --- |
| 백엔드 공통 구조·인증·로컬 실행 | [backend.md](backend.md) |
| 프론트엔드 구조·화면·로컬 실행 | [frontend.md](frontend.md) |
| 예매·모의 결제·취소·상태·API | [booking.md](booking.md) |
| 마이페이지 리포트·알림·탈퇴 | [mypageApi.md](mypageApi.md) |
| 관리자 권한·공연 관리 | [admin.md](admin.md) |
| 행동 이벤트 형식·전송·식별자 | [eventTracking.md](eventTracking.md) |
| 가상 프로필 구조·생성·확장 규칙 | [personaDataDesign.md](personaDataDesign.md) |
| 브라우저 자동화·두 API 부하 실행기·실행 기록 안내 | [playwrightGuide.md](playwrightGuide.md) |
| 이후 API 부하 실행기 명령·모델·중단 기준 | [실행기 README](../syntheticData/loadtest/README.md) |
| 부하 조건·시나리오·중단·재개 | [loadTestPlan.md](loadTestPlan.md) |
| 11월 6일 기존 API 실행 결과 | [loadTestResult.md](loadTestResult.md) |
| 11월 8일 마지막 전체 실행 결과 | [loadTestResult_claude_full4.md](loadTestResult_claude_full4.md) |
| 최신 IP·서버 역할·담당자 | [networkInfo.md](networkInfo.md) |
| 서버 구성 범위·미확정 자원 | [serverSpec.md](serverSpec.md) |
| 실서버 연결·HAProxy·nginx·TLS 절차 | [FrontToBackSetting.md](FrontToBackSetting.md) |
| 홈 화면의 기존 디자인 기준 | [homeDesign.md](homeDesign.md) |
| 커밋 메시지 규칙 | [gitCommitConvention.md](gitCommitConvention.md) |

## 과거 설계·작업 이력

아래는 작성 당시의 제안·작업 기록이다. 현재 실행 지침이나 미완료 작업 지시로 해석하지 않는다.
최신 구현과 실행 결과는 위 기준 문서를 우선한다.

- [초기 서버 배치 제안·자원 산정](serverSpec.md#초기-자원-산정과-설계-근거): 현재 구성 문서 안에 통합한 과거 설계 근거.
- [관리자 기능 구현 계획](superpowers/plans/2026-11-05-admin-performances.md): 2026-11-05 작업 기록.
- [마이페이지 구현 계획](superpowers/plans/2026-11-05-mypage-features.md): 2026-11-05 작업 기록.
- [부하 중단·재개 구현 계획](superpowers/plans/2026-11-06-load-test-resume.md): 2026-11-06 복구 기록.

삭제된 `sample/dist`용 시연판 안내는 제거했다. 현재 실행은 backend·frontend 안내를 따른다.
