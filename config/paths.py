# config/paths.py
# WHAT: 모든 입출력 파일 경로
# 경로를 바꿀 때 이 파일만 수정

from __future__ import annotations

from pathlib import Path

# ============================================================
# 프로젝트 루트 / 데이터 루트
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR     = PROJECT_ROOT / "data"

# ============================================================
# 단계별 데이터 디렉토리
# ============================================================
MANIFEST_DIR     = DATA_DIR / "00_manifest"   # 읽기 전용 원본 입력
PARSED_DIR       = DATA_DIR / "01_parsed"
CLEANSED_DIR     = DATA_DIR / "02_cleansed"
NORMALIZED_DIR   = DATA_DIR / "03_normalized"
FEATURES_DIR     = DATA_DIR / "04_features"
PREPROCESSED_DIR = DATA_DIR / "05_preprocessed"

# ============================================================
# 파일명 규칙
# ============================================================
# 레지스트리별 중간 파일: {registry}_{suffix}.csv
# 최종 통합 파일: features.csv

def parsed_path(registry: str) -> Path:
    return PARSED_DIR / f"{registry}_parsed.csv"

def cleansed_path(registry: str) -> Path:
    return CLEANSED_DIR / f"{registry}_cleansed.csv"

def normalized_path(registry: str) -> Path:
    return NORMALIZED_DIR / f"{registry}_normalized.csv"

FEATURES_PATH      = FEATURES_DIR      / "features.csv"
PREPROCESSED_PATH  = PREPROCESSED_DIR  / "preprocessed.csv"
