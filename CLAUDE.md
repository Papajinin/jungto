# Jungto 인계서

> 공통 규칙은 상위 폴더 `../CLAUDE.md`. 결정은 `plan/decisions.md`

- **무엇:** 정토불교대학 강의 노트 읽기 앱. **나(아빠)만 씀.** 브랜드 밖 앱 (자유 디자인, AIN 디자인 규칙 안 따름). 따뜻한 종이색 + 갈색, 글꼴은 고딕 하나
- **저작권:** 교재 원문·설명은 절대 공개하지 않는다. GitHub에는 코드만, 내용은 Firebase(`lectures/{01..}`, `meta/bigpicture`)에만, 내 계정만 읽기 (`firestore.rules`). `data/`는 `.gitignore`
- **파일:** `index.html`(틀·버전 확인), `style.css`, `app.js`(홈·읽기·원문/설명/연결 전환·큰 그림·목차·보기 설정), `sync.js`(로그인·내용 불러오기), `sync-config.js`(Firebase 설정값, 비어 있으면 맥의 `data/out/`에서 읽음), `tools/build.py`(내용 만들기), `tools/upload.html`(Firebase에 올리기), `manifest.json`·아이콘
- **내용 만들기 흐름:**
  1. 원본을 `data/raw/`에: 원문 `NN-orig.md`(또는 드라이브에서 가져온 `NN-orig-drive.md`), 설명 `NN-exp.md`(또는 `-drive.md`). 드라이브 원문 문서 끝의 `[설명 및 해석]`(제미나이 설명)은 build가 잘라 냄
  2. 정리 규칙 `data/diet.json` (강의별: I 앞머리 한 줄로 / K 앞머리에서 남길 문단 / S 문장 옮김 / P 문단 옮김 / H 큰 섹션 통째로 / C 표 칸 빼기). **원칙:** 그 강의 설명은 그대로, 앞 강의를 다시 꺼낸 부분만 "연결" 탭으로. 그 강의 논리에 꼭 필요한 한 줄은 남김. 강의별 판단 기록은 `data/diet-notes.md`
  3. 큰 그림 `data/bigpicture.json` (주제 → 강의별 한 줄, `at`은 설명 탭 제목 일부)
  4. `python3 tools/build.py` → `data/out/NN.json` (안 맞은 규칙은 끝에 "확인할 것"으로 나옴)
  5. 맥에서 `python3 -m http.server 8790` → `http://localhost:8790/`로 확인, `http://localhost:8790/tools/upload.html`로 올리기
- **원문 ↔ 설명 짝:** build가 설명 섹션 속 교재 인용문을 원문에서 찾아 자동으로 짝지음(`emap`). 연결 탭은 설명의 어느 큰 섹션에서 옮겼는지(`data-e`)로 따라감
- **읽던 곳·다 읽음·글자 크기·화면:** 이 기기에만 (localStorage `jungto.state`)
- **13강부터:** 새 파트(새 주제)의 1강이 시작됨. 사용자가 원문과 설명을 주면 같은 방식으로 추가. 설명은 강의마다 새 대화창에서 받기를 권함(한 대화창에서 이어 받으면 앞 강의 연결이 계속 길어짐)
- **버전:** 올릴 때마다 `index.html`의 `APP_VERSION`과 `version.txt`를 같이 올림. 지금 1

## 지켜볼 것 (실기기 확인)

> 단계: ① 올림 → ② 첫 확인 → ③ 써 보는 중 → ④ 완료 (공통 규칙 16번)

| 항목 | 상태 | 날짜 | 볼 것 |
|---|---|---|---|
| 첫 버전 1~12강 (v1) | 맥에서만 (Firebase·GitHub 전) | 11/26 | 홈 화면 추가, 로그인, 원문/설명/연결 전환이 보던 자리를 따라가는지, 큰 그림 누르면 그 자리로, 글자 크기·어둡게 |
