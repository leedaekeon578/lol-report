# LoL Report

닉네임#태그를 넣으면, 최근 소환사의 협곡 20매치 중 내 팀이 퍼스트블러드를 한 게임의 승패를 보여 주는 웹 페이지입니다.

## 앱이 하는 일

- 입력한 닉네임#태그의 최근 소환사의 협곡 매치를 20개 채워서, 그중 **내 팀이 퍼스트블러드를 한 게임**만 골라 보여 줍니다. 상대 팀이 퍼스트블러드를 한 게임은 포함하지 않고, 내가 직접 킬했는지는 묻지 않습니다. (PRD §3)
- 해당 게임 수, 승, 패, 승률을 요약하고, 해당 게임을 한 줄에 한 게임씩 목록으로 보여 줍니다.
- 소환사의 협곡 큐는 큐 420(랭크 솔로)과 440(랭크 자유)만 포함합니다. (D-004)
- 사용자는 본인 한 명, 서버는 KR만 지원하며, 데이터는 Riot API를 씁니다. (PRD §1)

## 구성과 실행

- 백엔드: Python 3.12 이상, FastAPI(uvicorn)
- 프론트엔드: React 19 + Vite + TypeScript
- 개발 중 화면의 `/api` 요청은 Vite 개발 서버가 백엔드(`127.0.0.1:8000`)로 넘깁니다. 그래서 백엔드를 8000번 포트로 실행해야 합니다. (D-013)

### 백엔드 (backend 폴더에서)

실행:

```
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

테스트:

```
.venv\Scripts\python -m unittest discover -s tests
```

2026-10-27 기준 45개 통과했습니다.

### 프론트엔드 (frontend 폴더에서)

| 목적 | 명령 |
|---|---|
| 실행 | `npm run dev` |
| 테스트 | `npm test` |
| lint | `npm run lint` |
| build | `npm run build` |

프론트엔드의 테스트, lint, build는 명령만 적었고 통과 여부는 이 문서에 기록하지 않았습니다.

프론트 주소는 `npm run dev` 실행 후 터미널에 나오는 주소로 접속합니다. 예시: http://localhost:5173/

## API 키

- Riot API 키는 서버에서만 쓰며 브라우저에는 노출하지 않습니다. (PRD R-009)
- 서버는 `backend/.env` 파일에서 키를 읽습니다. 변수 이름은 `backend/.env.example`을 참고합니다. (D-001)
- `.env`는 `.gitignore`로 Git에서 제외되며, 키는 Git에 넣지 않습니다. 이 저장소와 문서에는 키 값을 적지 않습니다.
- Riot 포털 문서에 개발 키는 24시간마다 비활성화된다고 적혀 있습니다. (PRD Q-04, Riot 포털 문서 기재)

## 문서 안내

- [AGENTS.md](AGENTS.md) — 이 저장소의 작업 규칙(브랜치, 변경 범위, 완료 보고)
- [ARCHITECTURE.md](ARCHITECTURE.md) — PRD를 화면 · API · 키 보관 · 데이터 흐름 구조로 옮긴 문서(상태: 작성 중)
- [DECISIONS.md](DECISIONS.md) — 결정 기록(D-001부터). 바뀌면 지우지 않고 새 번호를 추가함
- [PRD.md](PRD.md) — 제품 요구사항(상태: 확정)
- [PRODUCT-DIRECTION.md](PRODUCT-DIRECTION.md) — 처음 정한 제품 방향과 고정 조건
- [PROJECT-DISCOVERY.md](PROJECT-DISCOVERY.md) — 초기 요구사항 정리 기록(일부 내용은 이후 갱신되지 않음)

## 알려진 한계

문서에 적힌 내용만 옮겼습니다.

- **champion.first 해석**: 퍼스트블러드 판정은 `info.teams[].objectives.champion.first`를 씁니다. 필드 이름과 타입은 Riot 공식 문서와 일치하지만 이 필드의 뜻은 공식 문서에 설명이 없습니다. 저장한 실제 응답 20건 중 비교 가능한 18건을 대조해 확인했고(불일치 0), 비교 불가 2건이 있었습니다. (D-012)
- 협곡 큐는 420, 440만 포함하며 일반 큐는 포함하지 않습니다. (D-004)
- 20개를 채우려고 매치를 최대 100개까지 조회합니다. 20개를 못 채우면 채운 만큼 보여 주고 못 채웠다는 안내를 함께 보입니다. (D-005)
- 20개를 채우는 조회가 개인 키 호출 한도 안에 드는지는 확인하지 못했습니다. 한도 숫자는 공식 문서로 확인한 값이 아니라 전제로 쓰지 않습니다. (PRD Q-10, D-006)
- 이번 버전에서 만들지 않는 것: 로그인 · 다중 사용자, 지역 선택, 검색 기록, 캐싱 (PRD §4)

## 고지

> lol-report isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.
