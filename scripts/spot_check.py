# scripts/spot_check.py
# 의미적 정확성 스팟 체크 — UNKNOWN 정제 + 라이선스 피쳐
# 파이프라인과 독립 실행: python -m scripts.spot_check [--n N]

from __future__ import annotations

import argparse

import pandas as pd

from config.paths import parsed_path, cleansed_path, normalized_path, FEATURES_PATH
from config.registry_schema import PYPI_PLACEHOLDER_EXACT
from config.feature_schema import LICENSE_TAGS


# ============================================================
# 체크 1 — UNKNOWN 정제 (PyPI)
# ============================================================
_PYPI_CHECK_COLS = ["Summary", "Description", "License", "Author"]


def check_unknown_cleansing(n: int = 10) -> None:
    print("\n=== 체크 1: UNKNOWN 정제 (PyPI) ===")

    parsed   = pd.read_csv(parsed_path("pypi"),   low_memory=False)
    cleansed = pd.read_csv(cleansed_path("pypi"), low_memory=False)

    placeholders = set(PYPI_PLACEHOLDER_EXACT)

    # parsed에서 placeholder가 있는 행 찾기
    mask = parsed[_PYPI_CHECK_COLS].isin(placeholders).any(axis=1)
    samples = parsed[mask].head(n)

    if samples.empty:
        print("  UNKNOWN 값을 가진 패키지 없음")
        return

    for idx in samples.index:
        pkg_id = parsed.at[idx, "id"]
        print(f"\n  패키지: {pkg_id}")
        for col in _PYPI_CHECK_COLS:
            raw_val = parsed.at[idx, col]
            if raw_val not in placeholders:
                continue
            clean_val = cleansed.at[idx, col]
            ok = clean_val == "" or pd.isna(clean_val)
            tag = "PASS" if ok else "FAIL"
            print(f"    [{tag}] {col}: raw={raw_val!r}  →  cleansed={clean_val!r}")


# ============================================================
# 체크 2 — 라이선스 피쳐 (licenses_*_exist)
# ============================================================

def check_license_features(n: int = 10) -> None:
    print("\n=== 체크 2: 라이선스 피쳐 (licenses_*_exist) ===")

    features = pd.read_csv(FEATURES_PATH, low_memory=False)

    for registry in ["npm", "pypi", "rubygems"]:
        normalized = pd.read_csv(normalized_path(registry), low_memory=False)
        merged = normalized[["id", "licenses"]].merge(features[["id"] + [f"licenses_{t}_exist" for t in LICENSE_TAGS]], on="id")

        # licenses 컬럼이 비어있지 않은 행만 샘플링
        has_license = merged[merged["licenses"].notna() & (merged["licenses"] != "") & (merged["licenses"] != "[]")]
        samples = has_license.sample(min(n, len(has_license)), random_state=42) if not has_license.empty else has_license

        if samples.empty:
            print(f"\n  [{registry}] 라이선스 있는 패키지 없음")
            continue

        print(f"\n  [{registry}]")
        for _, row in samples.iterrows():
            raw = row["licenses"]
            tag_vals = {t: int(row[f"licenses_{t}_exist"]) for t in LICENSE_TAGS}
            # raw에 태그가 포함돼 있는데 피쳐가 0이거나, 없는데 1이면 의심
            raw_lower = raw.lower()
            suspicious = [
                t for t in LICENSE_TAGS
                if (t in raw_lower) != bool(tag_vals[t])
            ]
            flag = "  ← 불일치 의심" if suspicious else ""
            tag_str = "  ".join(f"{t}={v}" for t, v in tag_vals.items())
            print(f"    {'WARN' if suspicious else 'OK  '} raw={raw!r}")
            print(f"         {tag_str}{flag}")


# ============================================================
# 진입점
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=10, help="각 체크당 샘플 수")
    args = parser.parse_args()

    check_unknown_cleansing(n=args.n)
    check_license_features(n=args.n)
