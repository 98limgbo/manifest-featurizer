# scripts/validate.py
# 파이프라인 각 단계 출력물에 대한 구조적 검증
# 파이프라인과 독립 실행: python scripts/validate.py

from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.paths import (
    MANIFEST_DIR,
    FEATURES_PATH, PREPROCESSED_PATH,
    parsed_path, cleansed_path, normalized_path,
)
from config.registry_schema import (
    NORMALIZED_COLUMNS,
    NPM_RAW_NAME, NPM_RAW_VERSION,
    PYPI_RAW_NAME, PYPI_RAW_VERSION,
    RUBYGEMS_RAW_NAME, RUBYGEMS_RAW_VERSION,
)
from config.feature_schema import OUTPUT_COLUMNS
from config.preprocess_schema import LOG_TRANSFORM_FEATURES

# 파싱 단계 필드명은 레지스트리별 원본 필드명 사용
_PARSED_KEY_COLS = {
    "npm":      (NPM_RAW_NAME,      NPM_RAW_VERSION),
    "pypi":     (PYPI_RAW_NAME,     PYPI_RAW_VERSION),
    "rubygems": (RUBYGEMS_RAW_NAME, RUBYGEMS_RAW_VERSION),
}

# 정규화 후 선택 필드 — 빈 값이 정상이므로 NaN 허용
_OPTIONAL_NORMALIZED_COLS = {
    "summary_description", "homepage", "download", "bug_tracking", "source_repository",
}

_REGISTRIES = ["npm", "pypi", "rubygems"]
_PASS = "PASS"
_FAIL = "FAIL"
_INFO = "INFO"


def _result(label: str, ok: bool, msg: str) -> None:
    tag = _PASS if ok else _FAIL
    print(f"  [{tag}] {label}: {msg}")


def _info(label: str, msg: str) -> None:
    print(f"  [{_INFO}] {label}: {msg}")


# ============================================================
# 1단계 — 파싱
# ============================================================
def validate_parsed() -> None:
    print("\n=== 1단계: 파싱 (01_parsed) ===")
    for registry in _REGISTRIES:
        path = parsed_path(registry)
        if not path.exists():
            _result(registry, False, "파일 없음")
            continue

        df = pd.read_csv(path, low_memory=False)

        # 매니페스트 폴더 수 카운트
        manifest_count = sum(
            1
            for source_dir in MANIFEST_DIR.iterdir() if source_dir.is_dir()
            for label_dir in (source_dir / registry).iterdir()
            if label_dir.is_dir() and (source_dir / registry).exists()
            for pkg_dir in label_dir.iterdir() if pkg_dir.is_dir()
        )
        row_count = len(df)
        match = row_count == manifest_count
        _result(f"{registry} 행 수", match,
                f"파싱={row_count}  폴더={manifest_count}" + ("" if match else "  ← 불일치"))

        # 필수 필드 null 비율 (레지스트리별 원본 필드명 사용)
        name_col, version_col = _PARSED_KEY_COLS[registry]
        for col in [name_col, version_col]:
            if col not in df.columns:
                _result(f"{registry} {col}", False, "컬럼 없음")
                continue
            null_rate = df[col].isna().mean()
            _result(f"{registry} {col} null 비율", null_rate == 0,
                    f"{null_rate:.2%}")


# ============================================================
# 2단계 — 정제
# ============================================================
def validate_cleansed() -> None:
    print("\n=== 2단계: 정제 (02_cleansed) ===")
    for registry in _REGISTRIES:
        parsed = parsed_path(registry)
        cleansed = cleansed_path(registry)
        if not cleansed.exists():
            _result(registry, False, "파일 없음")
            continue

        n_parsed = len(pd.read_csv(parsed, low_memory=False))
        n_cleansed = len(pd.read_csv(cleansed, low_memory=False))
        match = n_parsed == n_cleansed
        _result(f"{registry} 행 수 유지", match,
                f"파싱={n_parsed}  정제={n_cleansed}" + ("" if match else "  ← 행 드롭 발생"))


# ============================================================
# 3단계 — 정규화
# ============================================================
def validate_normalized() -> None:
    print("\n=== 3단계: 정규화 (03_normalized) ===")
    frames = []
    for registry in _REGISTRIES:
        path = normalized_path(registry)
        if not path.exists():
            _result(registry, False, "파일 없음")
            continue

        df = pd.read_csv(path, low_memory=False)

        # 컬럼 일치 여부
        missing = [c for c in NORMALIZED_COLUMNS if c not in df.columns]
        extra   = [c for c in df.columns if c not in NORMALIZED_COLUMNS]
        _result(f"{registry} 컬럼 일치", not missing and not extra,
                "OK" if not missing and not extra
                else f"누락={missing}  초과={extra}")

        frames.append(df)

    # 합친 후 NaN 비율 (리스트 필드 제외 — 빈 리스트 [] 정상)
    if frames:
        combined = pd.concat(frames, ignore_index=True)
        id_cols = {"id", "source", "registry", "label"}
        list_cols = {"keywords", "files", "author_names", "author_emails",
                     "contributors_maintainer_names", "contributors_maintainer_emails",
                     "people_names", "people_emails", "licenses",
                     "dependencies", "runtime", "development", "optional", "requirement"}
        required_cols = [c for c in combined.columns
                         if c not in id_cols and c not in list_cols
                         and c not in _OPTIONAL_NORMALIZED_COLS]
        for col in required_cols:
            null_rate = combined[col].isna().mean()
            if null_rate > 0:
                _result(f"합친 후 {col} NaN", False, f"{null_rate:.2%}")
        _info("합치기", f"총 {len(combined)}행 ({len(frames)}개 레지스트리)")


# ============================================================
# 4단계 — 피쳐화
# ============================================================
def validate_features() -> None:
    print("\n=== 4단계: 피쳐화 (04_features) ===")
    if not FEATURES_PATH.exists():
        _result("features.csv", False, "파일 없음")
        return

    df = pd.read_csv(FEATURES_PATH, low_memory=False)

    # 컬럼 일치
    missing = [c for c in OUTPUT_COLUMNS if c not in df.columns]
    extra   = [c for c in df.columns if c not in OUTPUT_COLUMNS]
    _result("컬럼 일치", not missing and not extra,
            "OK" if not missing and not extra
            else f"누락={missing}  초과={extra}")

    # label 분포
    _info("label 분포", str(df["label"].value_counts().to_dict()))

    # 이진 피쳐: 0/1만 허용
    exist_cols = [c for c in df.columns if c.endswith("_exist")]
    bad_exist = [c for c in exist_cols if not df[c].isin([0, 1]).all()]
    _result("이진 피쳐(_exist) 값 범위", not bad_exist,
            "OK" if not bad_exist else f"이상 컬럼={bad_exist}")

    # 비율 피쳐: 0~1 범위
    ratio_cols = [c for c in df.columns if c.endswith("_ratio")]
    bad_ratio = [c for c in ratio_cols
                 if (df[c].dropna() < 0).any() or (df[c].dropna() > 1).any()]
    _result("비율 피쳐(_ratio) 값 범위", not bad_ratio,
            "OK" if not bad_ratio else f"이상 컬럼={bad_ratio}")

    # 수치 피쳐: 음수 없어야 함
    skip = set(exist_cols) | set(ratio_cols) | {"id", "source", "registry", "label"}
    num_cols = [c for c in df.select_dtypes(include="number").columns if c not in skip]
    bad_neg = [c for c in num_cols if (df[c].dropna() < 0).any()]
    _result("수치 피쳐 음수 없음", not bad_neg,
            "OK" if not bad_neg else f"음수 발생 컬럼={bad_neg}")


# ============================================================
# 5단계 — 전처리
# ============================================================
def validate_preprocessed() -> None:
    print("\n=== 5단계: 전처리 (05_preprocessed) ===")
    if not PREPROCESSED_PATH.exists():
        _result("preprocessed.csv", False, "파일 없음")
        return

    feat_df = pd.read_csv(FEATURES_PATH, low_memory=False)
    pre_df  = pd.read_csv(PREPROCESSED_PATH, low_memory=False)

    # 컬럼 수 동일
    _result("컬럼 수 유지", len(feat_df.columns) == len(pre_df.columns),
            f"피쳐={len(feat_df.columns)}  전처리={len(pre_df.columns)}")

    # 행 수 동일
    _result("행 수 유지", len(feat_df) == len(pre_df),
            f"피쳐={len(feat_df)}  전처리={len(pre_df)}")

    # log 변환 후 음수 없음
    bad_neg = [
        c for c in LOG_TRANSFORM_FEATURES
        if c in pre_df.columns and (pre_df[c].dropna() < 0).any()
    ]
    _result("log 변환 후 음수 없음", not bad_neg,
            "OK" if not bad_neg else f"음수 발생 컬럼={bad_neg}")

    # log 변환 전후 최대값 비교 (변환이 실제로 적용됐는지)
    shrank = [
        c for c in LOG_TRANSFORM_FEATURES
        if c in feat_df.columns and c in pre_df.columns
        and pd.to_numeric(feat_df[c], errors="coerce").max() > 1
        and pd.to_numeric(pre_df[c], errors="coerce").max()
            >= pd.to_numeric(feat_df[c], errors="coerce").max()
    ]
    _result("log 변환 적용 확인", not shrank,
            "OK" if not shrank else f"변환 미적용 의심 컬럼={shrank}")


# ============================================================
# 6단계 — 분포 비교 (malicious vs benign)
# ============================================================
_EXIST_DIRECTION = {
    # 악성 패키지에서 낮을 것으로 예상되는 피쳐
    "low":  [
        "summary_description_exist", "keywords_exist", "author_names_exist",
        "people_names_exist", "licenses_exist", "homepage_exist",
        "source_repository_exist", "bug_tracking_exist",
    ],
    # 악성 패키지에서 높을 것으로 예상되는 피쳐 (현재 없음 — 확장용)
    "high": [],
}


def validate_distribution() -> None:
    print("\n=== 6단계: 분포 비교 (malicious vs benign) ===")
    if not FEATURES_PATH.exists():
        _result("features.csv", False, "파일 없음")
        return

    df = pd.read_csv(FEATURES_PATH, low_memory=False)
    mal = df[df["label"] == "malicious"]
    ben = df[df["label"] == "benign"]

    if mal.empty or ben.empty:
        _result("분포 비교", False, "malicious 또는 benign 데이터 없음")
        return

    _info("샘플 수", f"malicious={len(mal)}  benign={len(ben)}")

    wrong = []
    for col in _EXIST_DIRECTION["low"]:
        if col not in df.columns:
            continue
        m_mean = mal[col].mean()
        b_mean = ben[col].mean()
        ok = m_mean < b_mean
        direction = "malicious < benign" if ok else "malicious >= benign  ← 예상 반대"
        print(f"  [{'PASS' if ok else 'FAIL'}] {col}: "
              f"malicious={m_mean:.3f}  benign={b_mean:.3f}  ({direction})")
        if not ok:
            wrong.append(col)

    if not wrong:
        _info("종합", "모든 피쳐가 예상 방향 일치")
    else:
        _result("종합", False, f"예상 반대 피쳐={wrong}")


# ============================================================
# 진입점
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("Meta2Vec 파이프라인 데이터 검증")
    print("=" * 50)
    validate_parsed()
    validate_cleansed()
    validate_normalized()
    validate_features()
    validate_preprocessed()
    validate_distribution()
    print("\n완료.")
