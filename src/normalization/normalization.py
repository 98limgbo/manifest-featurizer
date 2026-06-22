# src/normalization/normalization.py
# 필드명 통일 — 진입점: normalize(df, registry) -> pd.DataFrame
# 매핑 규칙은 config/registry_schema.py에서 import

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from config.registry_schema import (
    # 통합 컬럼명
    NORMALIZED_COLUMNS,
    COL_ID, COL_SOURCE, COL_REGISTRY, COL_LABEL, COL_DURATION,
    COL_NAME, COL_VERSION, COL_SUMMARY_DESCRIPTION,
    COL_KEYWORDS, COL_FILES,
    COL_AUTHOR_NAMES, COL_AUTHOR_EMAILS,
    COL_CONTRIB_MAINT_NAMES, COL_CONTRIB_MAINT_EMAILS,
    COL_PEOPLE_NAMES, COL_PEOPLE_EMAILS,
    COL_LICENSES,
    COL_DEPENDENCIES, COL_RUNTIME, COL_DEVELOPMENT, COL_OPTIONAL, COL_REQUIREMENT,
    COL_HOMEPAGE, COL_DOWNLOAD, COL_BUG_TRACKING, COL_SOURCE_REPOSITORY,
    # npm 원본 필드명
    NPM_RAW_NAME, NPM_RAW_VERSION, NPM_RAW_DESCRIPTION, NPM_RAW_KEYWORDS, NPM_RAW_FILES,
    NPM_RAW_AUTHOR, NPM_RAW_AUTHOR_EMAIL, NPM_RAW_CONTRIBUTORS, NPM_RAW_MAINTAINERS,
    NPM_RAW_LICENSE, NPM_RAW_LICENSES,
    NPM_RAW_HOMEPAGE, NPM_RAW_BUGS, NPM_RAW_REPOSITORY,
    NPM_RAW_DEPENDENCIES, NPM_RAW_DEV_DEPENDENCIES,
    NPM_RAW_OPTIONAL_DEPENDENCIES, NPM_RAW_PEER_DEPENDENCIES,
    # PyPI 원본 필드명
    PYPI_RAW_NAME, PYPI_RAW_VERSION, PYPI_RAW_SUMMARY, PYPI_RAW_DESCRIPTION,
    PYPI_RAW_KEYWORDS, PYPI_RAW_AUTHOR, PYPI_RAW_AUTHOR_EMAIL, PYPI_RAW_MAINTAINER,
    PYPI_RAW_LICENSE, PYPI_RAW_LICENSE_EXPRESSION,
    PYPI_RAW_HOME_PAGE, PYPI_RAW_DOWNLOAD_URL, PYPI_RAW_PROJECT_URL,
    PYPI_RAW_REQUIRES_DIST, PYPI_RAW_PROVIDES_EXTRA, PYPI_RAW_FILES,
    PYPI_PROJECT_URL_HOMEPAGE_PATTERNS, PYPI_PROJECT_URL_DOWNLOAD_PATTERNS,
    PYPI_PROJECT_URL_BUG_TRACKING_PATTERNS, PYPI_PROJECT_URL_SOURCE_REPO_PATTERNS,
    # RubyGems 원본 필드명
    RUBYGEMS_RAW_NAME, RUBYGEMS_RAW_VERSION, RUBYGEMS_RAW_SUMMARY, RUBYGEMS_RAW_DESCRIPTION,
    RUBYGEMS_RAW_AUTHORS, RUBYGEMS_RAW_EMAILS,
    RUBYGEMS_RAW_LICENSE, RUBYGEMS_RAW_LICENSES,
    RUBYGEMS_RAW_HOMEPAGE, RUBYGEMS_RAW_MD_HOMEPAGE_URI,
    RUBYGEMS_RAW_MD_BUG_TRACKER, RUBYGEMS_RAW_MD_SOURCE_CODE,
    RUBYGEMS_RAW_DEPS_RUNTIME, RUBYGEMS_RAW_DEPS_DEVELOPMENT, RUBYGEMS_RAW_FILES,
    RUBYGEMS_REQUIREMENT_JOINER,
)
from src.utils import try_parse_json, to_str as _to_str


def _to_str_list(value: Any, sort: bool = True) -> List[str]:
    """JSON list 셀 → 문자열 리스트. 스칼라도 단일 원소 리스트로 허용."""
    parsed = try_parse_json(value)
    if isinstance(parsed, list):
        out = [_to_str(x) for x in parsed if _to_str(x)]
        return sorted(set(out)) if sort else list(dict.fromkeys(out))
    s = _to_str(value)
    return [s] if s else []


def _merge_lists(*lists: List[str], sort: bool = True) -> List[str]:
    merged: List[str] = []
    for lst in lists:
        merged.extend(lst)
    return sorted(set(merged)) if sort else list(dict.fromkeys(merged))


def _to_json(lst: List[Any]) -> str:
    return json.dumps(lst, ensure_ascii=False)


def _extract_names_from_pairs(value: Any) -> List[str]:
    """[[name, spec], ...] → name 리스트 (index 0)."""
    parsed = try_parse_json(value)
    if not isinstance(parsed, list):
        return []
    out = []
    for row in parsed:
        if isinstance(row, (list, tuple)) and len(row) >= 1:
            s = _to_str(row[0])
            if s:
                out.append(s)
    return out


def _extract_index_from_triplets(value: Any, index: int) -> List[str]:
    """[[a, b, c], ...] → index번째 값 리스트."""
    parsed = try_parse_json(value)
    if not isinstance(parsed, list):
        return []
    out = []
    for row in parsed:
        if isinstance(row, (list, tuple)) and len(row) > index:
            s = _to_str(row[index])
            if s:
                out.append(s)
    return list(dict.fromkeys(out))


def _extract_url_from_pairs_or_scalar(value: Any, key: str) -> str:
    """string 또는 [[k,v],...] 에서 key에 해당하는 값 반환."""
    s = _to_str(value)
    if not s:
        return ""
    parsed = try_parse_json(s)
    if isinstance(parsed, list):
        for row in parsed:
            if isinstance(row, (list, tuple)) and len(row) >= 2:
                if _to_str(row[0]) == key:
                    return _to_str(row[1])
        return ""
    return s


def _build_summary_description(summary: Any, description: Any) -> str:
    s = _to_str(summary)
    d = _to_str(description)
    if s and d:
        return f"{s}\n\n{d}"
    return s or d


# ============================================================
# PyPI 전용 유틸
# ============================================================

def _norm_label(s: str) -> str:
    return re.sub(r"[\s\-_]+", "", s.lower())


def _extract_url_by_label(project_url_cell: Any, patterns: List[str]) -> str:
    """PyPI Project-URL에서 패턴 매칭으로 URL 추출."""
    parsed = try_parse_json(project_url_cell)
    if not isinstance(parsed, list):
        return ""
    norm_patterns = [_norm_label(p) for p in patterns if p]
    for row in parsed:
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            continue
        label = _norm_label(_to_str(row[0]))
        url   = _to_str(row[1])
        if not label or not url:
            continue
        if any(p in label for p in norm_patterns):
            return url
    return ""


def _extract_dist_name(req: str) -> str:
    """PEP 508 requirement 문자열에서 패키지명만 추출."""
    s = _to_str(req)
    if not s:
        return ""
    m = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)", s)
    return m.group(1).strip() if m else ""


def _extract_optional_names(requires_dist_cell: Any, provides_extra_cell: Any) -> List[str]:
    """Provides-Extra + Requires-Dist → optional 의존성 이름 리스트."""
    extras = set(_to_str_list(provides_extra_cell, sort=False))
    if not extras:
        return []
    reqs = _to_str_list(requires_dist_cell, sort=False)
    rx = re.compile(r"""extra\s*==\s*(['"])([^'"]+)\1""", re.IGNORECASE)
    out = []
    for req in reqs:
        for m in rx.finditer(req):
            if _to_str(m.group(2)) in extras:
                name = _extract_dist_name(req)
                if name:
                    out.append(name)
                break
    return out


# ============================================================
# RubyGems 전용 유틸
# ============================================================

def _extract_rubygems_dep_names(pairs_cell: Any) -> List[str]:
    """[[name, [req,...]], ...] → name 리스트."""
    parsed = try_parse_json(pairs_cell)
    if not isinstance(parsed, list):
        return []
    out = []
    for row in parsed:
        if isinstance(row, (list, tuple)) and len(row) >= 1:
            s = _to_str(row[0])
            if s:
                out.append(s)
    return out


# ============================================================
# 레지스트리별 정규화
# ============================================================

def _normalize_npm(row: pd.Series) -> Dict[str, Any]:
    author_names  = [s for s in [_to_str(row.get(NPM_RAW_AUTHOR))] if s]
    author_emails = [s for s in [_to_str(row.get(NPM_RAW_AUTHOR_EMAIL))] if s]

    contrib_names  = _extract_index_from_triplets(row.get(NPM_RAW_CONTRIBUTORS), 0)
    contrib_emails = _extract_index_from_triplets(row.get(NPM_RAW_CONTRIBUTORS), 1)
    maint_names    = _extract_index_from_triplets(row.get(NPM_RAW_MAINTAINERS), 0)
    maint_emails   = _extract_index_from_triplets(row.get(NPM_RAW_MAINTAINERS), 1)
    cm_names  = _merge_lists(contrib_names, maint_names)
    cm_emails = _merge_lists(contrib_emails, maint_emails)

    license_str  = _to_str(row.get(NPM_RAW_LICENSE))
    licenses_lst = _to_str_list(row.get(NPM_RAW_LICENSES))
    licenses = _merge_lists([license_str] if license_str else [], licenses_lst)

    bug_tracking      = _extract_url_from_pairs_or_scalar(row.get(NPM_RAW_BUGS), "url")
    source_repository = _extract_url_from_pairs_or_scalar(row.get(NPM_RAW_REPOSITORY), "url")

    dependencies = _extract_names_from_pairs(row.get(NPM_RAW_DEPENDENCIES))
    development  = _extract_names_from_pairs(row.get(NPM_RAW_DEV_DEPENDENCIES))
    optional     = _extract_names_from_pairs(row.get(NPM_RAW_OPTIONAL_DEPENDENCIES))
    requirement  = _extract_names_from_pairs(row.get(NPM_RAW_PEER_DEPENDENCIES))

    return {
        COL_NAME:                _to_str(row.get(NPM_RAW_NAME)),
        COL_VERSION:             _to_str(row.get(NPM_RAW_VERSION)),
        COL_SUMMARY_DESCRIPTION: _build_summary_description(None, row.get(NPM_RAW_DESCRIPTION)),
        COL_KEYWORDS:            _to_json(_to_str_list(row.get(NPM_RAW_KEYWORDS))),
        COL_FILES:               _to_json(_to_str_list(row.get(NPM_RAW_FILES))),
        COL_AUTHOR_NAMES:        _to_json(author_names),
        COL_AUTHOR_EMAILS:       _to_json(author_emails),
        COL_CONTRIB_MAINT_NAMES:   _to_json(cm_names),
        COL_CONTRIB_MAINT_EMAILS:  _to_json(cm_emails),
        COL_PEOPLE_NAMES:        _to_json(_merge_lists(author_names, cm_names)),
        COL_PEOPLE_EMAILS:       _to_json(_merge_lists(author_emails, cm_emails)),
        COL_LICENSES:            _to_json(licenses),
        COL_DEPENDENCIES:        _to_json(dependencies),
        COL_RUNTIME:             _to_json([]),
        COL_DEVELOPMENT:         _to_json(development),
        COL_OPTIONAL:            _to_json(optional),
        COL_REQUIREMENT:         _to_json(requirement),
        COL_HOMEPAGE:            _to_str(row.get(NPM_RAW_HOMEPAGE)),
        COL_DOWNLOAD:            "",
        COL_BUG_TRACKING:        bug_tracking,
        COL_SOURCE_REPOSITORY:   source_repository,
    }


def _normalize_pypi(row: pd.Series) -> Dict[str, Any]:
    author_names  = [s for s in [_to_str(row.get(PYPI_RAW_AUTHOR))] if s]
    author_emails = [s for s in [_to_str(row.get(PYPI_RAW_AUTHOR_EMAIL))] if s]
    maint_name    = _to_str(row.get(PYPI_RAW_MAINTAINER))
    cm_names  = [maint_name] if maint_name else []
    cm_emails: List[str] = []

    license_str  = _to_str(row.get(PYPI_RAW_LICENSE))
    license_expr = _to_str(row.get(PYPI_RAW_LICENSE_EXPRESSION))
    licenses = _merge_lists(
        [license_str] if license_str else [],
        [license_expr] if license_expr else [],
    )

    project_url = row.get(PYPI_RAW_PROJECT_URL)
    homepage = _to_str(row.get(PYPI_RAW_HOME_PAGE)) or \
               _extract_url_by_label(project_url, PYPI_PROJECT_URL_HOMEPAGE_PATTERNS)
    download = _to_str(row.get(PYPI_RAW_DOWNLOAD_URL)) or \
               _extract_url_by_label(project_url, PYPI_PROJECT_URL_DOWNLOAD_PATTERNS)
    bug_tracking      = _extract_url_by_label(project_url, PYPI_PROJECT_URL_BUG_TRACKING_PATTERNS)
    source_repository = _extract_url_by_label(project_url, PYPI_PROJECT_URL_SOURCE_REPO_PATTERNS)

    requires_dist = row.get(PYPI_RAW_REQUIRES_DIST)
    provides_extra = row.get(PYPI_RAW_PROVIDES_EXTRA)
    optional_names = _extract_optional_names(requires_dist, provides_extra)
    optional_set   = set(optional_names)
    all_reqs = _to_str_list(requires_dist, sort=False)
    dependencies = [_extract_dist_name(r) for r in all_reqs
                    if _extract_dist_name(r) and _extract_dist_name(r) not in optional_set]

    return {
        COL_NAME:                _to_str(row.get(PYPI_RAW_NAME)),
        COL_VERSION:             _to_str(row.get(PYPI_RAW_VERSION)),
        COL_SUMMARY_DESCRIPTION: _build_summary_description(
                                     row.get(PYPI_RAW_SUMMARY),
                                     row.get(PYPI_RAW_DESCRIPTION)),
        COL_KEYWORDS:            _to_json(_to_str_list(row.get(PYPI_RAW_KEYWORDS))),
        COL_FILES:               _to_json([]),
        COL_AUTHOR_NAMES:        _to_json(author_names),
        COL_AUTHOR_EMAILS:       _to_json(author_emails),
        COL_CONTRIB_MAINT_NAMES:   _to_json(cm_names),
        COL_CONTRIB_MAINT_EMAILS:  _to_json(cm_emails),
        COL_PEOPLE_NAMES:        _to_json(_merge_lists(author_names, cm_names)),
        COL_PEOPLE_EMAILS:       _to_json(_merge_lists(author_emails, cm_emails)),
        COL_LICENSES:            _to_json(licenses),
        COL_DEPENDENCIES:        _to_json(dependencies),
        COL_RUNTIME:             _to_json([]),
        COL_DEVELOPMENT:         _to_json([]),
        COL_OPTIONAL:            _to_json(optional_names),
        COL_REQUIREMENT:         _to_json([]),
        COL_HOMEPAGE:            homepage,
        COL_DOWNLOAD:            download,
        COL_BUG_TRACKING:        bug_tracking,
        COL_SOURCE_REPOSITORY:   source_repository,
    }


def _normalize_rubygems(row: pd.Series) -> Dict[str, Any]:
    author_names  = _to_str_list(row.get(RUBYGEMS_RAW_AUTHORS))
    author_emails = _to_str_list(row.get(RUBYGEMS_RAW_EMAILS))

    license_str  = _to_str(row.get(RUBYGEMS_RAW_LICENSE))
    licenses_lst = _to_str_list(row.get(RUBYGEMS_RAW_LICENSES))
    licenses = _merge_lists([license_str] if license_str else [], licenses_lst)

    homepage = _to_str(row.get(RUBYGEMS_RAW_HOMEPAGE)) or \
               _to_str(row.get(RUBYGEMS_RAW_MD_HOMEPAGE_URI))
    bug_tracking      = _to_str(row.get(RUBYGEMS_RAW_MD_BUG_TRACKER))
    source_repository = _to_str(row.get(RUBYGEMS_RAW_MD_SOURCE_CODE))

    runtime_names = _extract_rubygems_dep_names(row.get(RUBYGEMS_RAW_DEPS_RUNTIME))
    dev_names     = _extract_rubygems_dep_names(row.get(RUBYGEMS_RAW_DEPS_DEVELOPMENT))

    return {
        COL_NAME:                _to_str(row.get(RUBYGEMS_RAW_NAME)),
        COL_VERSION:             _to_str(row.get(RUBYGEMS_RAW_VERSION)),
        COL_SUMMARY_DESCRIPTION: _build_summary_description(
                                     row.get(RUBYGEMS_RAW_SUMMARY),
                                     row.get(RUBYGEMS_RAW_DESCRIPTION)),
        COL_KEYWORDS:            _to_json([]),
        COL_FILES:               _to_json(_to_str_list(row.get(RUBYGEMS_RAW_FILES))),
        COL_AUTHOR_NAMES:        _to_json(author_names),
        COL_AUTHOR_EMAILS:       _to_json(author_emails),
        COL_CONTRIB_MAINT_NAMES:   _to_json([]),
        COL_CONTRIB_MAINT_EMAILS:  _to_json([]),
        COL_PEOPLE_NAMES:        _to_json(author_names),
        COL_PEOPLE_EMAILS:       _to_json(author_emails),
        COL_LICENSES:            _to_json(licenses),
        COL_DEPENDENCIES:        _to_json(runtime_names),
        COL_RUNTIME:             _to_json(runtime_names),
        COL_DEVELOPMENT:         _to_json(dev_names),
        COL_OPTIONAL:            _to_json([]),
        COL_REQUIREMENT:         _to_json([]),
        COL_HOMEPAGE:            homepage,
        COL_DOWNLOAD:            "",
        COL_BUG_TRACKING:        bug_tracking,
        COL_SOURCE_REPOSITORY:   source_repository,
    }


# ============================================================
# 진입점
# ============================================================

_NORMALIZERS = {
    "npm":      _normalize_npm,
    "pypi":     _normalize_pypi,
    "rubygems": _normalize_rubygems,
}


def normalize(df: pd.DataFrame, registry: str) -> pd.DataFrame:
    """
    레지스트리별 원본 필드명 → 통합 필드명으로 변환.
    출력 컬럼은 NORMALIZED_COLUMNS 순서로 고정.
    """
    normalizer = _NORMALIZERS.get(registry)
    if normalizer is None:
        raise ValueError(f"지원하지 않는 레지스트리: {registry}")

    meta_cols = [COL_ID, COL_SOURCE, COL_REGISTRY, COL_LABEL]
    normalized_rows = df.apply(normalizer, axis=1)
    normalized_df   = pd.DataFrame(normalized_rows.tolist())

    out = pd.concat([df[meta_cols].reset_index(drop=True),
                     df[[COL_DURATION]].reset_index(drop=True),
                     normalized_df.reset_index(drop=True)], axis=1)

    # 스키마 컬럼 순서 강제 + 누락 컬럼 빈 값으로 채우기
    for col in NORMALIZED_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    return out[NORMALIZED_COLUMNS]
