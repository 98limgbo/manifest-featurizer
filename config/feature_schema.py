# config/feature_schema.py
# WHAT: 정규화 후 통합 필드명 기반 피쳐 정의
# 피쳐를 추가/제거할 때 이 파일만 수정
# HOW(계산 로직)는 src/features/features.py 참고

from __future__ import annotations
from typing import List

# ============================================================
# 식별 컬럼 (피쳐 아님 — 출력 CSV에 함께 포함)
# ============================================================
ID_COLUMNS: List[str] = ["id", "source", "registry", "label"]

# ============================================================
# 라이선스 태그 (SPDX 정규화 후 substring 매칭)
# ============================================================
LICENSE_TAGS: List[str] = ["mit", "apache", "gpl", "bsd", "isc"]

# ============================================================
# 피쳐 목록 (그룹별)
# ============================================================

# 이름
NAME_FEATURES: List[str] = [
    "name_exist",
    "name_length",
]

# 버전
VERSION_FEATURES: List[str] = [
    "version_exist",
    "version_major",
    "version_minor",
    "version_patch",
]

# 설명
SUMMARY_DESCRIPTION_FEATURES: List[str] = [
    "summary_description_exist",
    "summary_description_length",
]

# 키워드
KEYWORDS_FEATURES: List[str] = [
    "keywords_exist",
    "keywords_count",
    "keywords_length_avg",
]

# 파일
FILES_FEATURES: List[str] = [
    "files_count",
]

# 사람
PEOPLE_FEATURES: List[str] = [
    "author_names_exist",
    "people_names_exist",
    "people_names_count",
    "people_names_length_avg",
    "people_emails_length_avg",
]

# 라이선스
LICENSES_FEATURES: List[str] = [
    "licenses_exist",
    "licenses_count",
    "licenses_length_avg",
    "licenses_mit_exist",
    "licenses_apache_exist",
    "licenses_gpl_exist",
    "licenses_bsd_exist",
    "licenses_isc_exist",
]

# 의존성
DEPENDENCIES_FEATURES: List[str] = [
    "dependencies_exist",
    "dependencies_count",
    "dependencies_length_avg",
    "runtime_exist",
    "runtime_count",
    "runtime_ratio",
    "development_exist",
    "development_count",
    "development_ratio",
    "optional_exist",
    "optional_count",
    "optional_ratio",
    "requirement_exist",
    "requirement_count",
    "requirement_ratio",
]

# URL
URL_FEATURES: List[str] = [
    "homepage_exist",
    "homepage_length",
    "download_exist",
    "download_length",
    "bug_tracking_exist",
    "bug_tracking_length",
    "source_repository_exist",
    "source_repository_length",
]

# ============================================================
# 전체 피쳐 목록 (출력 컬럼 순서)
# ============================================================
ALL_FEATURES: List[str] = (
    NAME_FEATURES
    + VERSION_FEATURES
    + SUMMARY_DESCRIPTION_FEATURES
    + KEYWORDS_FEATURES
    + FILES_FEATURES
    + PEOPLE_FEATURES
    + LICENSES_FEATURES
    + DEPENDENCIES_FEATURES
    + URL_FEATURES
)

# ============================================================
# 최종 출력 컬럼 순서 (식별 컬럼 + 피쳐)
# ============================================================
OUTPUT_COLUMNS: List[str] = ID_COLUMNS + ALL_FEATURES
