# OFFMate 사용자 프롬프트 기록

- 기록 범위: OFFMate 프로젝트 최초 설계 요청부터 2026-08-16 현재 요청까지
- 기록 방식: 사용자 요청을 시간 순서대로 정리
- 이미지 입력: 이미지 자체 대신 화면과 요청의 의미를 설명
- 보안 처리: Access Key 값, 개인 자격 증명 파일의 절대 경로 등은 기록하지 않음
- 참고: 오탈자와 짧은 후속 지시는 의도를 보존하기 위해 가능한 한 원문 그대로 기록함

## 1. 최초 설계 요청

```text
친구 기반 숏폼 패널티 앱 설계 요청
현재 연결된 저장소와 모든 관련 파일을 먼저 조사해줘.
지금 단계에서는 코드를 구현하거나 기존 파일을 수정하지 말고, 요구사항·기술적 실현 가능성·시스템 구조·MVP 범위를 분석하여 구체적인 구현 계획만 작성해줘.
답변은 한국어로 작성하되, 코드상의 클래스명·API명·상태명·AWS 리소스명은 영어를 사용해줘.

⸻

1. 제품 개요
우리가 만들려는 서비스는 친구에게 자신의 숏폼 사용 통제 권한을 일부 맡기는 소셜 디지털 웰빙 앱이다.
핵심 철학은 다음과 같다.
혼자서 숏폼을 끊는 것이 아니라, 친구와 약속하고 친구가 부여한 패널티를 수행한 뒤 현실 활동 인증을 통해 다시 자유를 얻는다.

⸻

2. 핵심 사용자 흐름
사용자 역할
* User A: 숏폼 사용 제한과 패널티를 수행하는 사용자
* User B: A의 친구이자 패널티를 부여하고 인증 결과를 확인하는 사용자
* 하나의 사용자가 상황에 따라 A와 B 역할을 모두 수행할 수 있다.
* 여러 사용자가 하나의 Group에 참여할 수 있다.
기본 흐름
1. A가 로그인한다.
2. A가 B를 친구로 추가한다.
3. A와 B가 그룹을 생성하거나 기존 그룹에 참여한다.
4. A가 숏폼 이용 가능을 설정 40분 , 20분 등
    * 제한 대상 예: Instagram, YouTube, TikTok
5. 설정 시간 이후로 Penalty Window가 시작된다.
6. Penalty Window 안에서만 B가 A에게 패널티를 부여할 수 있다.
7. 패널티 예시는 다음과 같다.
    * 앱 완전 차단
    * 흑백 화면
    * 영상 0.5배속
    * 소리 끄기
8. 패널티가 적용된 동안 A는 숏폼 대신 수행한 현실 활동의 인증 사진을 촬영하여 제출한다.
9. AI가 인증 사진을 분석한다.
    * 책을 읽거나 공부하는 사진이면 PASS
    * 게임이나 숏폼을 보는 사진이면 FAIL
    * 불명확하거나 확신이 낮으면 HUMAN_REVIEW
10. PASS이면 해당 세션이 종료되고 패널티가 해제된다.
11. FAIL이면 패널티가 유지되거나 더 강한 패널티가 적용되고 A는 다시 인증해야 한다.
12. HUMAN_REVIEW이면 B가 최종 판단한다.
13. 사용자가 다시 진행하려면 새로운 이용 시간대를 설정하고 같은 흐름을 반복한다.

⸻

3. 먼저 해결해야 할 핵심 모호성
아래 항목은 임의로 숨기지 말고, 합리적인 기본값을 제안한 뒤 결정이 필요한 부분을 별도로 표시해줘.
1. 설정한 시간대 가 끝나는 즉시 패널티가 자동 시작되는가? 예스
2. 아니면 오후 4시부터 B가 패널티를 부여할 수 있는 권한만 활성화되는가? 예스
3. B가 아무 패널티도 선택하지 않으면 A에게 어떤 상태가 적용되는가? 자동적으로 자기가 선택환 모드로 돌아가기
4. Penalty Window의 종료 시각은 어떻게 정하는가? 모든 것은 20분 제한
5. 인증 사진을 제출하지 않으면 패널티는 언제까지 유지되는가? 계속
6. A가 여러 장의 사진을 반복 제출할 수 있는가? 1장만
7. AI의 FAIL 판정을 B가 뒤집을 수 있는가? no
8. B가 A의 앱 사용 기록을 수준까지 볼 수 있는가? 없음
9. 그룹에 여러 친구가 있다면 누가 패널티를 부여할 수 있는가? 랜덤
10. 한 명의 승인이 필요한가, 과반수 승인이 필요한가? 예스
11. 긴급 상황에서 A가 사용할 수 있는 안전 해제 기능은 무엇인가? 없음
12. 앱 전체를 제한할 것인지, Reels·Shorts 기능만 제한할 것인지? 영상에 대한 모든것

⸻

4. 필수 Feasibility Gate
가장 먼저 다음 세 가지 구현 경로를 비교해줘.
Option A: 실제 Instagram·YouTube 네이티브 앱 제어
* iOS FamilyControls
* DeviceActivity
* ManagedSettings
* Android UsageStatsManager
* Android Overlay 또는 Accessibility 관련 제약
Option C: 모바일 웹 또는 브라우저 확장
* YouTube Shorts나 Instagram Web에 CSS·JavaScript 기반 패널티 적용
* 모바일 앱과 웹 확장 간 연동 가능성
각 옵션을 다음 기준으로 평가해줘.
* 실제 구현 가능성
* 앱스토어 정책 위험
* 해커톤 기간 내 구현 가능성
* 친구가 원격으로 패널티를 부여할 수 있는지
* 백그라운드 상태에서도 적용 가능한지
* 흑백·배속·음소거 구현 가능 여부
* iOS와 Android 차이
* 데모 안정성
* 실제 서비스 확장성
외부 앱의 세부 재생 상태를 제어할 수 없는 경우 이를 구현한 것처럼 가장하지 말아줘.
그 경우 다음과 같은 이중 구조를 우선 검토해줘.
* 실제 기기 제어 MVP: 앱 전체 shield 또는 block
* 해커톤 데모: 자체 숏폼 플레이어에서 흑백·배속·음소거 패널티 구현
최종적으로 하나의 권장 플랫폼과 MVP 구현 방식을 선택하고 이유를 설명해줘.

⸻

5. 권장 상태 머신 설계
아래 흐름을 참고하되 더 안전하고 일관된 상태 머신으로 수정해줘.
DRAFT
→ SCHEDULED
→ VIEWING_WINDOW_ACTIVE
→ PENALTY_WINDOW_OPEN
→ PENALTY_APPLIED
→ PROOF_PENDING
→ AI_ANALYZING
→ PASS
   └→ COMPLETED
→ FAIL
   └→ PROOF_PENDING 또는 ESCALATED_PENALTY
→ HUMAN_REVIEW
   ├→ PASS
   └→ FAIL
→ EXPIRED
→ CANCELLED

⸻

6. AI VLM 인증 사진 분석 설계
AI가 사진을 직접 보고 도덕적으로 PASS 또는 FAIL을 임의 판단하게 하지 말고, 다음과 같이 역할을 분리하는 방식을 우선 검토해줘.
인증 사진
→ Vision AI가 활동 후보 추출
→ PASS / FAIL / HUMAN_REVIEW 결정
→ AI가 사용자에게 판정 이유 설명
예:
Image Analysis:
detected_activity = reading_book
confidence = 0.93

Group Policy:
self_development
→ ALLOWED_BY
→ Group A

Decision:
PASS
게임 사진 예:
Image Analysis:
detected_activity = playing_video_game
confidence = 0.91

Knowledge Graph:
playing_video_game
→ CONFLICTS_WITH
→ focus_goal

Group Policy:
focus_goal
→ REQUIRED_BY
→ Group A

Decision:
FAIL
AI 출력은 반드시 구조화된 JSON으로 제한하는 설계를 제안해줘.
예시 스키마:
{
  "analysis_id": "analysis_123",
  "detected_activities": [
    {
      "activity_id": "reading_book",
      "confidence": 0.93,
      "visual_evidence": [
        "open book",
        "user looking at pages"
      ]
    }
  ],
  "decision": "PASS",
  "decision_confidence": 0.91,
  "matched_policy_ids": [
    "policy_self_development"
  ],
  "reason": "The image provides sufficient evidence of a permitted reading activity.",
  "requires_human_review": false
}
⸻
8. AWS 아키텍처 설계
다음 기능을 중심으로 최소 AWS 구성을 제안해줘.
* Cognito: A와 B 로그인
* API Gateway 또는 AppSync: 모바일 API
* Lambda: 도메인 로직
* DynamoDB: 사용자, 친구, 그룹, 세션, 패널티, 판정 상태
* EventBridge Scheduler: 이용 시간 종료 및 Penalty Window 시작
* Step Functions: 인증 제출, AI 분석, 사람 검토 워크플로
* S3: 인증 사진
* Bedrock: 이미지 기반 활동 분석
* Neptune: 정책 및 활동 관계
* Push Notification: B에게 패널티 요청, A에게 판정 결과 전달
* CloudWatch: 로그, 메트릭, 추적
각 서비스마다 다음을 적어줘.
* 정확한 책임
* 해당 서비스가 필요한 이유
* 제거 가능한지
* 로컬 개발 대체 방법
* 예상 장애 지점
* 해커톤 MVP 포함 여부
서비스를 많이 사용하는 것 자체를 목표로 하지 말고, P0·P1·P2로 구분해줘.

⸻

9. 데이터 모델과 API
다음 엔티티를 포함한 데이터 모델을 설계해줘.
* User
* Friendship
* Group
* GroupMembership
* ViewingSchedule
* ViewingSession
* PenaltyWindow
* Penalty
* ProofSubmission
* AIAnalysis
* PolicyDecision
* Notification
* AuditEvent
각 엔티티에 대해 다음을 작성해줘.
* 필드
* primary key
* secondary index
* 상태
* 생성·수정 시각
* actor
* idempotency key
* TTL이 필요한 데이터
필요한 REST API 또는 GraphQL operation도 정의해줘.
예:
POST /friends/invitations
POST /groups
POST /groups/{groupId}/members
POST /viewing-schedules
GET  /viewing-sessions/{sessionId}
POST /viewing-sessions/{sessionId}/penalties
POST /proofs/upload-url
POST /proofs/{proofId}/submit
GET  /proofs/{proofId}/analysis
POST /reviews/{reviewId}/approve
POST /reviews/{reviewId}/reject
POST /sessions/{sessionId}/emergency-unlock
각 쓰기 API에는 인증, 권한, 상태 전이 조건, idempotency 전략을 포함해줘.

⸻

10. 보안·개인정보·악용 방지
이 서비스가 친구나 연인에 의한 통제 수단으로 악용되지 않도록 다음 규칙을 설계에 포함해줘.
* A가 명시적으로 동의한 그룹과 일정에서만 B가 패널티를 부여할 수 있음
* B가 임의로 제한 앱이나 시간을 변경할 수 없음
* 약속 변경은 A의 재동의 필요
* A는 긴급 해제 또는 약속 종료 요청 가능
* B는 A의 화면 내용, DM, 검색 기록을 볼 수 없음
* 인증 사진은 지정된 그룹과 AI 분석 시스템만 접근 가능
* 인증 사진 보존 기간 설정
* 얼굴 인식 및 신원 추정 금지
* 모든 패널티와 판정에 감사 로그 생성
* 친구 관계가 종료되면 모든 제어 권한 즉시 무효화
* AI가 패널티를 임의 생성하거나 강화하지 못함
* AI가 직접 앱 잠금 해제 또는 승인 API를 호출하지 못함

⸻

11. Codex·MCP·Harness 설계
Codex
Codex가 다음 역할을 수행하도록 설계해줘.
* 모바일 코드 구현
* AWS 백엔드 구현
* IaC 작성
* AI 평가 코드 작성
* Knowledge Graph query 작성
* 테스트 작성
* 문서 업데이트
MCP
Codex가 다음 시스템을 조회하거나 개발 환경에서만 실행하도록 구성해줘.
* GitHub
* Harness
* AWS 개발 환경
* 공식 문서
* 테스트 결과
Production 쓰기 권한은 제공하지 않는 구조로 설계해줘.
Harness Pipeline
다음 stage를 포함하는 CI/CD 계획을 작성해줘.
Pull Request Trigger
→ Lint
→ Type Check
→ Unit Test
→ State Machine Test
→ API Contract Test
→ AI Vision Evaluation
→ KG Policy Grounding Test
→ Security Scan
→ IaC Plan
→ Dev Deployment
→ End-to-End Test
→ Human Approval
AI 평가에서 최소한 다음을 검증해줘.
* JSON schema validity
* 허용되지 않은 Activity ID 생성 여부
* KG에 없는 Policy ID 생성 여부
* PASS·FAIL·HUMAN_REVIEW 정확도
* 낮은 confidence에서 자동 PASS하지 않는지
* 이미지 속 텍스트 prompt injection에 영향을 받는지
* AI가 unlock 또는 penalty API를 호출하려 하는지

⸻

12. 테스트 시나리오
최소한 다음 End-to-End 시나리오를 설계해줘.
Scenario A: 책 읽기 PASS
1. A 로그인
2. B 친구 추가
3. 그룹 생성
4. 오후 2시~4시 이용 일정 생성
5. 시간을 테스트 방식으로 오후 4시 이후로 이동
6. B가 패널티 적용
7. A가 책 읽는 인증 사진 제출
8. AI가 reading_book 감지
9. KG 정책과 매칭
10. PASS
11. 패널티 해제
12. 세션 종료
Scenario B: 게임 FAIL
1. 동일한 흐름으로 새 세션 생성
2. B가 패널티 적용
3. A가 게임하는 인증 사진 제출
4. AI가 playing_video_game 감지
5. KG 정책과 충돌
6. FAIL
7. 패널티 유지
8. 재인증 요구
Scenario C: 불명확한 사진
1. 활동을 식별하기 어려운 사진 제출
2. confidence threshold 미달
3. HUMAN_REVIEW
4. B가 최종 판단
Scenario D: 안전성
* B가 Penalty Window 밖에서 패널티 적용 시도
* 그룹 외 사용자가 패널티 적용 시도
* 동일 요청을 두 번 전송
* 만료된 세션에 사진 제출
* AI 분석 API timeout
* Bedrock 사용 불가
* 사진 upload 실패
* A가 긴급 해제 사용
* 친구 관계가 해제된 뒤 B가 제어 시도

⸻

13. 최종 산출물 형식
아래 순서로 계획을 작성해줘.
1. 저장소 현황과 재사용 가능한 코드
2. 요구사항 재정의
3. 미결정 사항과 추천 기본값
4. 플랫폼별 feasibility matrix
5. 최종 권장 MVP
6. 시스템 아키텍처
7. 사용자 흐름
8. 상태 머신
9. AWS 서비스 책임
10. 데이터 모델
11. API 및 이벤트
12. AI 인증 분석 구조
13. Knowledge Graph 구조
14. 보안과 악용 방지
15. Codex·MCP·Harness 구조
16. 테스트 및 AI 평가 전략
17. P0·P1·P2 구현 범위
18. 파일·모듈 단위 구현 순서
19. 예상 일정과 위험 요소
20. 사용자에게 확인받아야 할 최종 결정
각 구현 단계에는 다음을 명시해줘.
* 변경할 파일 또는 디렉터리
* 선행 조건
* 구현 내용
* 검증 명령
* 완료 기준
* 실패 시 대안
마지막에는 반드시 다음 세 목록을 작성해줘.
반드시 먼저 결정할 항목
해커톤 MVP에서 제외할 항목
구현을 시작하기 전에 사용자가 승인해야 할 권장안
계획이 끝나기 전까지 코드를 수정하거나 AWS 리소스를 생성하지 말아줘.
GPU 사용은 내가 runpod 사용하니까 해당 계정을 알려줄게
```

## 2. 요구사항 확정 및 범위 조정

### 2.1 기본값 표에 대한 지시

주석 맥락: `BLOCKGRAYSCALEPLAYBACK_RATE_0_5`

| 항목 | 권장 기본값 | 확인 필요 |
|---|---|---|
| 일정 종료와 패널티 시작 | 종료 즉시 `defaultPenalty` 자동 적용 | 승인 필요 |
| B 권한 | 같은 시점에 20분간 활성화 | 승인 필요 |
| B가 미선택 | A의 기본 패널티 유지, B 권한만 종료 | 승인 필요 |
| `PenaltyWindow` | 20분 | 확인 |
| 패널티 지속 | `PASS`, 안전 해제, 동의 철회까지 | 확인 |
| 사진 수 | 제출당 1장, `FAIL` 후 새 제출 가능 | “세션 전체 1장”인지 확인 |
| AI `FAIL` 뒤집기 | 불가 | 확정으로 간주 |
| AI 저신뢰/장애 | `HUMAN_REVIEW` | 승인 필요 |
| 그룹 제어자 | 세션 시작 때 활동 회원 중 1명 무작위 선정 | 승인 필요 |
| 다수결 | MVP 제외, 선정된 1명만 판단 | “과반수 예스” 답변과 충돌 |
| 검토자 20분 무응답 | 안전을 위해 패널티 해제 | 승인 필요 |
| 긴급 해제 | A 전용, 즉시 적용, 감사 로그·cooldown | 필수 승인 |
| 대상 범위 | A가 고른 앱 전체 shield | 기능별 제어 불가 |
| 패널티 강화 | 사전 동의한 고정 ladder만 허용 | 승인 필요 |

```text
내가 준거만 맞고 안 준거는 하지마

그리고 궁금하게 데모를 어떻게 보여주는거지? 안드로이드 스튜디오는 스마트폰 화면 자체가 보여지는데 이거는 어떻게?

그리고
https://www.console.runpod.io/

여기서 내거 runpod mcp 연결시켜서 vlm 모델 서빙하자
```

### 2.2 페이지와 저장소 연결

```text
페이지 안보녀
```

```text
https://github.com/Codex-Hackaton/hackathon 이 깃허브랑 연결해서 동작하자 기록하고자 하는 역할이야

이슈 같은것들도 적극적으로 활용해줘

그리고 UI는 내가 나중에 줄게

그리고 AWS도 연결해야하는거 아니야?
```

```text
다싲 ㅓ봐
```

```text
AWS 승인 창을 다시줘
```

```text
너무 많은 것들을 깃허브에 남기려고 하지마
```

### 2.3 구현 시작과 UI

```text
오키 이제 구현 시작하자
```

```text
https://www.figma.com/make/3cqcp5JIHOvBDGK0aHR2jS/Create-platform?fullscreen=1

이거 UI 따라서 개발해
```

```text
지금 구현 중인거지?
```

```text
Figma 권한 내가 어케줄까
```

이미지 첨부: Figma `Share this file` 창. `Anyone can view` 상태와 초대된 편집자 목록이 표시됨.

```text
하고 있지?
```

```text
[로컬 ZIP 경로 생략] 이거 참고해
```

### 2.4 Xcode Simulator와 실제 서비스

```text
Xcode 설치 후 같은 SwiftUI 화면을 iPhone Simulator로 옮길 수 있습니다.

이렇게 하려면 어떻게 해야하는거지? 나는 simulator를 띄우기를 원하는데
```

```text
그러면 구현은 거의 한건가?
```

```text
실제 서비스 구현하고 있어 설치가 시간이 걸려
```

```text
내가 보기에 0.5배속이 구현이 불가능하다고 보니 화면에 장애물같이 사람이 릴스 보는데 불편하게 하는거로 바꾸자
```

```text
얼마나 걸리는지 알려줄수 있어?
```

```text
그러면 기능 구현은 어느정도 남은거지?
```

```text
우선 우리는 MVP를 중점으로 수행하는것을 목표로 하고 배포는 시간이 있으면 추가적으로 수행하자
```

### 2.5 Simulator 오류와 클라우드 연결

```text
어떤 것이 문제인거지?
```

이미지 첨부: `MobileCal 응용 프로그램이 예기치 않게 종료되었습니다.` crash report. `process-launch watchdog transgression`, `0x8BADF00D`, 30초 제한 초과가 표시됨.

```text
AWS 연결은 잘 수행하고 있는거지? runpod도
```

```text
왜 안했어 그거 하고 있어 여기도 해놔야지

각가 돈이 어느정도는 들어가 있어서 연결도 수행해야돼

내가 plan mode에서 넣은 내용들 기반으로 구축해
```

```text
지금 내가 준 aws에 25달러가 들어가 있어서 그거 사용할 수도 있어
```

```text
이게 failed가 뜨는 거가 문제인건가?
```

이미지 첨부: Xcode 26.6의 Components 다운로드 화면. `iOS 26.5 Simulator`가 `Failed — Duplicate of ...`로 표시됨.

```text
그거 하면서 AWS 연결이 잘 안된거 같으면 그 부분도 같이 다듬으면서 업데이트하자

AWS 최소 기능 구현하고 Xcode로 데모는 가능하게 해야돼
```

### 2.6 목표 아키텍처와 데모 스토리

```text
이거가 어느 정도는 구현이 되었으면 좋겠어 내가 생각하는 아키텍처야
```

이미지 첨부: `친구 기반 숏폼 패널티 앱 - REST API 기반 시스템 구조` 다이어그램. Mobile Clients, API Gateway, Lambda, DynamoDB, Cognito, S3, Bedrock/Neptune, SNS/FCM, EventBridge, 주요 REST API와 예시 흐름이 포함됨.

```text
step functions가 뭐지? vlm불러와서 실제 평가하는거는 구현이 필요한 작업인데
```

```text
데모 스토리를 짜줄게

1. 처음 페이지에서 설정하고
2. 설정한거에 맞춰서 유튜브를 보다가 이제 시간이 되었을 때 친구로부터 패널티 부연된거가 적용이 되는거지
3. 그러면 그 때 캡쳐본에서 이미지를 갖고와 사진을 업로드하고 vlm으로 패스가 되면 종료되는 스토리로 진행해볼거야
그래서 이 정도 구축은 해놔야하는 상태인거지
```

```text
지금 어느 정도까지 구축이 된거지? AWS에 들어가면 아무것도 안나오는데
```

### 2.7 AWS 콘솔 설정

주석 맥락:

> AWS 쪽은 그림의 모든 서비스를 그대로 복제하지 않고, 이 데모에 실제로 필요한 경로만 구현합니다. DynamoDB(세션/판정 저장), S3(사진), Lambda(FastAPI 및 VLM worker), Step Functions(분석 orchestration), Cognito/API Gateway(인증·진입점)만 P0로 두고, Neptune과 SNS는 이번 데모 범위에서 제외합니다. RunPod는 Bedrock 위치를 대체합니다.

```text
여기서 어디를 들어가라는거야?
```

이미지 첨부: AWS Console Home, 서울 리전. 최근 방문 서비스로 DynamoDB, CloudWatch, EC2, 결제 및 비용 관리가 표시됨.

이미지 첨부: AWS 무료 플랜 상태. 남은 크레딧과 남은 일수가 표시됨.

이미지 첨부: IAM 사용자 `OFFMateDev`가 성공적으로 생성된 화면.

이미지 첨부: IAM 사용자 `OFFMateDev`의 정책 생성 JSON 편집 화면.

```text
했어
```

```text
[AWS Access Key CSV의 개인 로컬 경로 생략]
```

```text
그러면 이거 연결 되면 AWS도 구현이 끝인건가?
나는 데모 영상을 만들고 싶은데
```

```text
얼마나 걸릴까? 예상 소요 시간
```

```text
그래도 우선 완성은 해야하니까..... 한 20분 안에는 마치는 것으로 목표를 하자
```

```text
지금 작업하고있는 진행 상황이랑 최소한으로 남은 것들을 알려줘
```

이미지 첨부: AWS Secrets Manager 화면. `Amazon DocumentDB 클러스터 목록을 가져오지 못했습니다` 및 `The AWS Access Key Id needs a subscription for the service` 메시지가 표시됨.

```text
저장했어
```

### 2.8 데모 진행 및 오류 수정

```text
얼마나 걸릴까
```

```text
뭐래

데모 영상 녹화는 내가 할건데?
```

```text
지금까지 한거를 나한테 보여주는 방식으로 한자
```

이미지 첨부: YouTube 시청 데모 화면. Swift 문자열 보간이 누락되어 `(configuredMinutes)`, `(remainingDemoSeconds)`가 그대로 표시되고 `API 409: expected state VIEWING_WINDOW_ACTIVE, got COMPLETED` 오류가 나타남.

이미지 첨부: 현실 활동 인증 화면. `서버 연결에 실패했습니다: The data couldn’t be read because it is missing.` 오류가 나타남.

```text
다시 시작하고 싶어이제 데모 영상 찍을거라서
```

### 2.9 앱 아이콘과 GitHub 업로드

```text
이거 앱을 이모티콘으로 바꿔줘
```

이미지 첨부: Simulator 홈 화면의 기본 격자형 OFFMate placeholder 아이콘.

```text
응 그거로 바꿔
```

```text
됐다 여기까지 하고 github 올리자
```

### 2.10 프롬프트 문서화

```text
지금까지의 내가 준 프롬프트를 md 파일로도 만들어줘
```

### 2.11 프롬프트 기록 GitHub 반영

```text
그것도 푸쉬해서 올려줘
```
