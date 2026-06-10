# manifest-featurizer — 프로젝트 컨텍스트

## 목적
매니페스트 파일에서 메타데이터를 추출해 악성 패키지 탐지용 피쳐를 생성하는 **데이터 준비 파이프라인**.  
탐지(모델 추론)는 이 프로젝트의 범위 밖이다.

## 파이프라인 흐름
```
00_manifest → [파싱] → 01_parsed → [정제] → 02_cleansed
→ [정규화] → 03_normalized → [합치기+피쳐화] → 04_features
→ [전처리] → 05_preprocessed
```

## 데이터 구조
```
data/00_manifest/{source}/{registry}/{label}/
```
- `source`: `old`(과거 수집) / `new`(최근 수집)
- `registry`: `npm` / `pypi` / `rubygems`
- `label`: `malicious` / `benign` / `spam`(npm 한정) / `disputed` 등 확장 가능
  - `disputed`: benign으로 수집됐으나 악성으로 확인된 패키지 (docs/disputed_packages.md 참고)

**패키지 ID 형식**
```
source::registry::label::name::version
예) old::npm::malicious::evil-pkg::1.0.0
```
ID는 파싱 시점에 폴더 경로에서 자동 생성.

## 코드 탐색 가이드 (질문 → 파일)

| 질문 | 파일 |
|---|---|
| 파일 경로가 어디야? | `config/paths.py` |
| 레지스트리별 원본 필드명이 뭐야? | `config/registry_schema.py` |
| placeholder 규칙이 뭐야? | `config/registry_schema.py` |
| 피쳐가 뭐야? / 피쳐 그룹이 뭐야? | `config/feature_schema.py` |
| 어떤 피쳐에 로그 변환을 적용해? | `config/preprocess_schema.py` |
| npm 파싱이 어떻게 돼? | `src/parsing/npm.py` |
| 정제 로직이 어떻게 돼? | `src/cleansing/cleansing.py` |
| 정규화 로직이 어떻게 돼? | `src/normalization/normalization.py` |
| 피쳐 계산이 어떻게 돼? | `src/features/features.py` |
| 피쳐 전처리(로그 변환)가 어떻게 돼? | `src/preprocessing/preprocessing.py` |
| 폴더 순회 / ID 생성이 어떻게 돼? | `src/loader.py` |
| 전체 흐름이 어떻게 돼? | `src/pipeline.py` |
| CSV 읽기/쓰기가 어떻게 돼? | `src/utils.py` |
| 파이프라인 출력물 검증이 어떻게 돼? | `scripts/validate.py` |
| UNKNOWN 정제 / 라이선스 피쳐 스팟 체크가 어떻게 돼? | `scripts/spot_check.py` |
| 외부 경로 패키지를 data에 넣는 방법은? | `scripts/ingest_packages.py` |
| 샘플 데이터는 어떻게 추출해? | `scripts/sample_packages.py` |

> **원칙: config = WHAT (값·규칙·이름), src = HOW (동작 방식)**

## 폴더 구조
```
manifest-featurizer/
├── config/
│   ├── paths.py              # 모든 입출력 파일 경로
│   ├── registry_schema.py    # 레지스트리별 원본 필드명 매핑 + placeholder 규칙
│   ├── feature_schema.py     # 피쳐 정의 + LICENSE_TAGS
│   └── preprocess_schema.py  # 전처리 변환 규칙 (LOG_TRANSFORM_FEATURES)
├── data/
│   ├── 00_manifest/          # 원본 입력 (읽기 전용)
│   ├── 01_parsed/            # 레지스트리별 CSV
│   ├── 02_cleansed/          # 값 정제 후
│   ├── 03_normalized/        # 필드명 통일 후
│   ├── 04_features/          # 피쳐화 결과 (features.csv)
│   ├── 05_preprocessed/      # 로그 변환 후 최종 결과 (preprocessed.csv)
│   └── sample/               # 샘플 데이터 (00_manifest와 동일 구조)
├── pyproject.toml            # 의존성 정의 (uv로 관리)
├── docs/                     # 비공개 메모 (.gitignore)
│   └── disputed_packages.md  # 재분류된 패키지 목록 및 경위
├── scripts/                  # 유틸리티 (move_disputed.py만 .gitignore)
│   ├── move_disputed.py      # disputed 패키지 폴더 이동 스크립트 (일회성, .gitignore)
│   ├── validate.py           # 파이프라인 출력물 구조적 검증 (독립 실행)
│   ├── spot_check.py         # 의미적 정확성 스팟 체크 (독립 실행)
│   ├── ingest_packages.py    # 외부 아카이브에서 매니페스트 추출 (독립 실행)
│   └── sample_packages.py    # 샘플 데이터 추출 (독립 실행, 일회성)
└── src/
    ├── parsing/
    │   ├── npm.py            # npm 매니페스트 파서 (진입점: parse_npm_package_json)
    │   ├── pypi.py           # pypi 파서 (진입점: parse_pypi_pkg_info)
    │   └── rubygems.py       # rubygems 파서 (진입점: parse_rubygems_metadata)
    ├── cleansing/
    │   └── cleansing.py      # 정제 로직 (진입점: cleanse). 규칙은 config에서 import
    ├── normalization/
    │   └── normalization.py  # 필드명 통일 (진입점: normalize). 매핑은 config에서 import
    ├── features/
    │   └── features.py       # 피쳐 생성 (진입점: featurize). 이진+길이+개수+버전 피쳐
    ├── preprocessing/
    │   └── preprocessing.py  # 피쳐 전처리 (진입점: preprocess). log1p 변환
    ├── loader.py             # 폴더 순회 + 경로에서 메타데이터 추출 + ID 생성 + 파서 디스패치
    ├── utils.py              # load_csv / save_csv / ensure_dir / try_parse_json / to_str
    └── pipeline.py           # 전체 흐름 순차 실행 + 레지스트리 합치기
```

## 각 모듈 역할 요약

### config/paths.py
모든 파일 경로 한 곳에서 관리. 경로를 바꿀 때 이 파일만 수정.

### config/registry_schema.py
- 레지스트리별 원본 필드명 → 통합 필드명 매핑
- 레지스트리별 placeholder 제거 규칙 (PyPI: `UNKNOWN`, RubyGems: `TODO:` 등)
- 새 레지스트리 추가 시 이 파일에 항목 추가

### config/feature_schema.py
- 통합 필드명 목록 (정규화 후 기준)
- 메타데이터 그룹별 피쳐 셀렉션 정의
- `LICENSE_TAGS`: SPDX 정규화 후 substring 매칭할 라이선스 종류
- 피쳐를 추가/제거할 때 이 파일만 수정

### config/preprocess_schema.py
- `LOG_TRANSFORM_FEATURES`: np.log1p를 적용할 피쳐 목록
- 이진 피쳐(_exist)와 비율 피쳐(_ratio)는 제외
- 전처리 규칙을 추가/변경할 때 이 파일만 수정

### src/loader.py
- `00_manifest/{source}/{registry}/{label}/` 폴더 순회
- 경로에서 `source`, `registry`, `label` 자동 추출
- registry에 맞는 파서 디스패치
- `id`(`source::registry::label::name::version`) 및 메타데이터 컬럼 부여
- 새 레지스트리 추가 시 `_REGISTRY_CONFIG`에 항목 한 줄 추가

### src/parsing/
- 매니페스트 텍스트 하나 → 필드 dict 하나 반환
- 폴더 순회·ID 생성·메타데이터 부여는 loader.py 담당

### src/cleansing/cleansing.py
- NaN/None → `""` 통일
- 레지스트리별 placeholder 제거 (규칙은 `registry_schema.py`에서 읽음)
- JSON 리스트 셀 내부 정제 및 중복 제거
- `CleanseStats`로 정제 통계 반환

### src/normalization/normalization.py
- 레지스트리별 필드명 → 통합 필드명으로 변환
- 리스트 필드는 `json.dumps`로 직렬화해 저장
- 매핑은 `registry_schema.py`에서 읽음

### src/features/features.py
- 이진 피쳐: 필드 존재 여부 (0/1)
- 길이/개수 피쳐: 문자열·리스트 길이 및 개수 (로그 변환 전 원본값)
- 버전 피쳐: major/minor/patch 숫자 (로그 변환 전 원본값)
- 라이선스: SPDX 정규화 후 통계 + LICENSE_TAGS 기반 태그 피쳐
- 의존성 비율: 전체 대비 각 타입 비율
- 피쳐 정의는 `feature_schema.py`에서 읽음

### src/preprocessing/preprocessing.py
- `LOG_TRANSFORM_FEATURES`에 정의된 피쳐에 `np.log1p` 적용
- 스케일링(모델 학습 직전)과 구분되는 값 변환 단계
- 변환 대상은 `preprocess_schema.py`에서 읽음

### src/pipeline.py
- 파싱 → 정제 → 정규화 → 합치기 → 피쳐화 → 전처리 순차 실행
- 3개 레지스트리 CSV를 정규화 후 하나로 합침 (이 시점에 컬럼 일치)

### src/utils.py
- `load_csv`, `save_csv`, `ensure_dir`: CSV I/O
- `try_parse_json`: JSON 문자열 셀 파싱 (cleansing + normalization + features 공용)
- `to_str`: 값 → 문자열 변환, None/NaN → `""` (normalization + features 공용)

### scripts/validate.py
- 파이프라인 각 단계 출력물(01~05) 구조적 검증. 파이프라인과 독립 실행
- 실행: `python -m scripts.validate`
- 체크 항목: 행 수·컬럼 일치, 필수 필드 null, 값 범위(이진/비율/수치), log 변환 적용, malicious vs benign 분포 방향

### scripts/spot_check.py
- 의미적 정확성 스팟 체크. 파이프라인과 독립 실행
- 실행: `python -m scripts.spot_check [--n N]`
- 체크 항목: PyPI `UNKNOWN` placeholder 정제 결과, 라이선스 raw 값 vs `licenses_*_exist` 피쳐 일치 여부

### scripts/ingest_packages.py
- 외부 경로의 패키지 아카이브에서 매니페스트를 추출해 `data/00_manifest`에 저장
- 실행: `python -m scripts.ingest_packages <source_dir> <registry> <label> [--source new]`
- 중복 스킵, 실패 목록 `logs/`에 저장, `_REGISTRY_CONFIG`로 레지스트리 확장 가능
- 현재 npm(`.tgz`) 지원. pypi·rubygems는 `_REGISTRY_CONFIG`에 항목 추가로 확장

### scripts/sample_packages.py
- `03_normalized` CSV에서 조건 필터링 후 label별 1개씩 샘플링해 `data/sample/`에 복사
- 실행: `python -m scripts.sample_packages [--seed N]`
- 조건: licenses에 "mit" 포함 + 매니페스트 파싱 name·version 비어있지 않음

## 함수 시그니처 (압축 후 참조용)

| 모듈 | 함수 | 시그니처 |
|---|---|---|
| `src/loader.py` | `load_registry` | `(registry: str, manifest_dir: Path) -> pd.DataFrame` |
| `src/parsing/npm.py` | `parse_npm_package_json` | `(text: str) -> dict` |
| `src/parsing/pypi.py` | `parse_pypi_pkg_info` | `(text: str) -> dict` |
| `src/parsing/rubygems.py` | `parse_rubygems_metadata` | `(text: str) -> dict` |
| `src/cleansing/cleansing.py` | `cleanse` | `(df: pd.DataFrame, registry: str) -> Tuple[pd.DataFrame, dict]` |
| `src/normalization/normalization.py` | `normalize` | `(df: pd.DataFrame, registry: str) -> pd.DataFrame` |
| `src/features/features.py` | `featurize` | `(df: pd.DataFrame) -> pd.DataFrame` |
| `src/preprocessing/preprocessing.py` | `preprocess` | `(df: pd.DataFrame) -> pd.DataFrame` |
| `src/utils.py` | `load_csv` | `(path: Path) -> pd.DataFrame` |
| `src/utils.py` | `save_csv` | `(df: pd.DataFrame, path: Path) -> None` |
| `src/utils.py` | `ensure_dir` | `(path: Path) -> None` |
| `src/utils.py` | `try_parse_json` | `(value: Any) -> Optional[Any]` |
| `src/utils.py` | `to_str` | `(value: Any) -> str` |

## 확장 가이드

### 새 레지스트리 추가 (예: maven)
1. `data/00_manifest/{source}/maven/{label}/` 폴더 생성
2. `src/parsing/maven.py` 파서 작성
3. `config/registry_schema.py`에 필드 매핑 + placeholder 규칙 추가
4. `src/loader.py`의 `_REGISTRY_CONFIG`에 항목 추가

### 새 label 추가 (예: npm spam)
1. `data/00_manifest/new/npm/spam/` 폴더 생성
2. 코드 변경 없음 (label을 경로에서 자동 추출)

### 전처리 규칙 변경
1. `config/preprocess_schema.py`의 `LOG_TRANSFORM_FEATURES` 수정
2. 코드 변경 없음
