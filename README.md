# OFFMate

친구와 합의한 숏폼 이용 시간 이후 패널티를 적용하고, 현실 활동 사진을 인증해 세션을 종료하는 iOS 앱과 API 구현입니다.

현재 SwiftUI 화면은 로컬 FastAPI에 연결됩니다. Figma Make의 `OFFMatecode.zip`은 UI 참고 자료로만 사용하며 Git에는 포함하지 않습니다.

- `backend/`: FastAPI, 세션 상태 전이, 20분 `PenaltyWindow`, 사진 업로드, 권한 및 AI 판정 검증
- `contracts/`: RunPod VLM이 반환해야 하는 JSON Schema
- `ios/`: iOS App target, SwiftUI, API client 및 도메인 모델
- `ios/Sources/PenaltyDemoApp/`: 온보딩, 규칙 설정, 홈, 친구 제어자, 패널티, AI 사진 인증 화면
- `runpod_worker/`: Qwen2.5-VL 활동 추출 worker와 고정 policy 판정

패널티 종류는 요구사항에 명시된 네 가지로 제한합니다.

- `BLOCK`
- `GRAYSCALE`
- `OBSTRUCTION`
- `MUTED`

## 검증

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m unittest discover -s tests -v

# SwiftUI보다 먼저 API 실행. 세션은 SQLite에 유지됩니다.
OFFMATE_DB_PATH=.local/offmate.sqlite3 \
  .venv/bin/uvicorn penalty_app.api:app --host 127.0.0.1 --port 8000

# 새 터미널
cd ../ios
swift test

# macOS에서 스마트폰 비율의 발표용 앱 창 실행
swift run PenaltyDemoApp
```

## 데모 순서

1. 온보딩에서 `규칙 정하러 가기`를 선택합니다.
2. 20분 또는 40분과 기본 패널티를 정하고 홈으로 이동합니다.
3. `이용 시간 종료 데모`를 눌러 기본 패널티 자동 적용을 보여줍니다.
4. `친구 B 화면`에서 무작위 선정자와 20분 `Penalty Window`를 보여주고 패널티를 선택합니다.
5. 활동 사진 1장 제출 화면에서 책, 게임, 불명확 샘플을 골라 각각 `PASS`, `FAIL`, `HUMAN_REVIEW` 흐름을 보여줍니다.

위 흐름은 실제 HTTP API, 단일 사용 업로드 슬롯, idempotency, A/B 권한 검사와 연결됩니다. RunPod 환경변수가 없을 때만 로컬 deterministic VLM adapter를 사용합니다.

Xcode와 iOS Simulator runtime이 설치되면 동일한 SwiftUI 코드를 iPhone 화면에서 실행할 수 있습니다.

## iPhone Simulator 실행

저장소에는 Simulator용 iOS App target인 `ios/OFFMate.xcodeproj`가 포함되어 있습니다.

1. Mac App Store에서 Xcode를 설치하고 한 번 실행해 추가 구성요소 설치를 완료합니다.
2. 터미널에서 아래 명령을 실행합니다.

```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
sudo xcodebuild -runFirstLaunch
open ios/OFFMate.xcodeproj
```

3. Xcode 상단에서 Scheme은 `OFFMate`, 기기는 설치된 iPhone Simulator를 선택합니다.
4. ▶ Run 버튼 또는 `Command + R`을 누릅니다.

Xcode에서 iPhone 목록이 비어 있으면 `Xcode > Settings > Platforms`에서 iOS Simulator Runtime을 내려받습니다. Simulator에서도 Mac의 API는 `http://127.0.0.1:8000`으로 접근합니다.

## RunPod 연결

queue-based Serverless endpoint를 생성한 뒤 backend 실행 전에 설정합니다.

```bash
export RUNPOD_ENDPOINT_ID="..."
export RUNPOD_API_KEY="..."
export RUNPOD_MODEL_ID="Qwen/Qwen2.5-VL-3B-Instruct"
```

API key는 iOS 앱에 넣지 않고 backend에서만 보관합니다. Worker 빌드와 policy 테스트 방법은 `runpod_worker/README.md`를 참고하세요.

`RUNPOD_API_KEY`는 iOS 앱이나 Git 저장소에 저장하지 않습니다. Backend는
RunPod의 OpenAI-compatible VLM endpoint로 사진을 전송하고, VLM의 활동 추출
결과에 backend의 고정 정책을 적용합니다.
