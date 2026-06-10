# src/pipeline.py
# 전체 파이프라인 순차 실행 — 진입점: run()

from __future__ import annotations

from typing import Dict, List

import pandas as pd

from config.paths import (
    MANIFEST_DIR,
    FEATURES_PATH, PREPROCESSED_PATH,
    parsed_path, cleansed_path, normalized_path,
)
from src.loader import load_registry
from src.cleansing.cleansing import cleanse
from src.normalization.normalization import normalize
from src.features.features import featurize
from src.preprocessing.preprocessing import preprocess
from src.utils import save_csv, ensure_dir

_REGISTRIES = ["npm", "pypi", "rubygems"]


def _print_stats(label: str, counts: Dict[str, int]) -> None:
    print(f"  [{label}]", "  ".join(f"{k}={v}" for k, v in counts.items()))


def run() -> None:
    ensure_dir(FEATURES_PATH.parent)
    ensure_dir(PREPROCESSED_PATH.parent)

    normalized_frames: List[pd.DataFrame] = []

    for registry in _REGISTRIES:
        print(f"\n=== {registry} ===")

        # 1. 파싱
        parsed = load_registry(registry, MANIFEST_DIR)
        save_csv(parsed, parsed_path(registry))
        print(f"  파싱: {len(parsed)}행")

        # 2. 정제
        cleansed, stats = cleanse(parsed, registry)
        save_csv(cleansed, cleansed_path(registry))
        _print_stats("정제", stats)

        # 3. 정규화
        norm = normalize(cleansed, registry)
        save_csv(norm, normalized_path(registry))
        print(f"  정규화: {len(norm)}행")

        normalized_frames.append(norm)

    # 4. 합치기
    combined = pd.concat(normalized_frames, ignore_index=True)
    print(f"\n=== 합치기: {len(combined)}행 ({len(_REGISTRIES)}개 레지스트리) ===")

    # 5. 피쳐화
    features = featurize(combined)
    save_csv(features, FEATURES_PATH)
    print(f"=== 피쳐화: {len(features)}행 × {len(features.columns)}컬럼 → {FEATURES_PATH.name} ===")

    # 6. 전처리
    preprocessed = preprocess(features)
    save_csv(preprocessed, PREPROCESSED_PATH)
    print(f"=== 전처리: {len(preprocessed)}행 × {len(preprocessed.columns)}컬럼 → {PREPROCESSED_PATH.name} ===")


if __name__ == "__main__":
    run()
