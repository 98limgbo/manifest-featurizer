# config/preprocess_schema.py
# WHAT: 피쳐 전처리 규칙 — 어떤 피쳐에 어떤 변환을 적용할지
# HOW(변환 로직)는 src/preprocessing/preprocessing.py 참고

from __future__ import annotations
from typing import List

# ============================================================
# 로그 변환 대상 피쳐 (np.log1p 적용)
# 이진 피쳐(_exist)와 비율 피쳐(_ratio)는 제외
# ============================================================
LOG_TRANSFORM_FEATURES: List[str] = [
    # 길이
    "name_length",
    "summary_description_length",
    "keywords_length_avg",
    "people_names_length_avg",
    "people_emails_length_avg",
    "licenses_length_avg",
    "dependencies_length_avg",
    "homepage_length",
    "download_length",
    "bug_tracking_length",
    "source_repository_length",
    # 개수
    "keywords_count",
    "files_count",
    "people_names_count",
    "licenses_count",
    "dependencies_count",
    "runtime_count",
    "development_count",
    "optional_count",
    "requirement_count",
    # 버전 숫자
    "version_major",
    "version_minor",
    "version_patch",
]
