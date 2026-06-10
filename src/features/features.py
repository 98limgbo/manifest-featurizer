# src/features/features.py
# 피쳐 생성 — 진입점: featurize(df) -> pd.DataFrame
# 피쳐 정의는 config/feature_schema.py에서 import

from __future__ import annotations

import re
from typing import List, Tuple

import numpy as np
import pandas as pd

import spdx_license_list
from license_expression import get_spdx_licensing

_SPDX_MAP: dict = {}
for _id, _obj in spdx_license_list.LICENSES.items():
    _SPDX_MAP[_id.lower()] = _id
    _SPDX_MAP[_obj.name.lower()] = _id

_SPDX_LICENSING = get_spdx_licensing()

from config.feature_schema import (
    ID_COLUMNS, OUTPUT_COLUMNS,
    NAME_FEATURES, VERSION_FEATURES, SUMMARY_DESCRIPTION_FEATURES,
    KEYWORDS_FEATURES, FILES_FEATURES, PEOPLE_FEATURES,
    LICENSES_FEATURES, DEPENDENCIES_FEATURES, URL_FEATURES,
    LICENSE_TAGS,
)
from config.registry_schema import (
    COL_DEPENDENCIES, COL_RUNTIME, COL_DEVELOPMENT, COL_OPTIONAL, COL_REQUIREMENT,
)
from src.utils import try_parse_json, to_str as _to_str

_DEP_RATIO_COLS = [COL_RUNTIME, COL_DEVELOPMENT, COL_OPTIONAL, COL_REQUIREMENT]
_LICENSE_EXPR_SPLIT_RE = re.compile(r"\b(?:and|or|with)\b|[(),;]", flags=re.IGNORECASE)
_EMPTY_LICENSE_LITERALS = {"", "nan", "none", "null", "[]"}


# ============================================================
# 공통 유틸
# ============================================================


def _parse_to_list(value: object) -> List[str]:
    """CSV 셀 → 문자열 리스트. JSON list 우선, 실패 시 콤마 분리."""
    parsed = try_parse_json(value)
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    s = _to_str(value)
    if not s or s.lower() in ("nan", "none"):
        return []
    return [item.strip() for item in s.split(",") if item.strip()]


# ============================================================
# 피쳐 계산 함수
# ============================================================

def _list_metrics(value: object) -> Tuple[int, int, float]:
    """(exist, count, avg_length)"""
    lst = _parse_to_list(value)
    count = len(lst)
    if count == 0:
        return (0, 0, 0.0)
    return (1, count, sum(len(x) for x in lst) / count)


def _version_metrics(value: object) -> Tuple[int, int, int, int]:
    """(exist, major, minor, patch)"""
    s = _to_str(value)
    if not s or s.lower() in ("nan", "none"):
        return (0, 0, 0, 0)
    parts = re.findall(r"\d+", s)
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    exist = 1 if parts else 0
    return (exist, major, minor, patch)


def _normalize_license(token: str) -> str:
    return _SPDX_MAP.get(token.lower().strip(), token.lower().strip())


def _license_tokens(expr: str) -> List[str]:
    text = expr.strip()
    if not text or text.lower() in _EMPTY_LICENSE_LITERALS:
        return []
    try:
        parsed = _SPDX_LICENSING.parse(text)
        symbols = getattr(parsed, "symbols", None)
        if symbols is not None:
            if callable(symbols):
                symbols = symbols()
            tokens = [str(getattr(s, "key", None) or getattr(s, "value", s)).strip()
                      for s in symbols]
            tokens = [t for t in tokens if t]
            if tokens:
                return tokens
    except Exception:
        pass
    return [t.strip() for t in _LICENSE_EXPR_SPLIT_RE.split(text) if t.strip()]


def _normalize_licenses(value: object) -> List[str]:
    """라이선스 값 → SPDX 정규화된 토큰 리스트."""
    raw_list = _parse_to_list(value)
    tokens: List[str] = []
    for chunk in raw_list:
        tokens.extend(_license_tokens(chunk))
    seen: set = set()
    out: List[str] = []
    for t in tokens:
        norm = _normalize_license(t)
        if "unknown" in norm.lower():
            continue
        key = norm.lower()
        if key not in seen:
            seen.add(key)
            out.append(norm)
    return out


# ============================================================
# 컬럼 그룹별 피쳐 생성
# ============================================================

def _string_features(df: pd.DataFrame, col: str) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    series = df[col].astype(str).replace(["nan", "None", ""], pd.NA)
    out[f"{col}_exist"]   = series.notna().astype(int)
    out[f"{col}_length"]  = series.fillna("").str.len()
    return out


def _list_features(df: pd.DataFrame, col: str,
                   with_exist: bool = True,
                   with_count: bool = True,
                   with_avg: bool = True) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    metrics = df[col].apply(_list_metrics)
    if with_exist:
        out[f"{col}_exist"]      = metrics.apply(lambda x: x[0])
    if with_count:
        out[f"{col}_count"]      = metrics.apply(lambda x: x[1])
    if with_avg:
        out[f"{col}_length_avg"] = metrics.apply(lambda x: x[2])
    return out


def _version_features(df: pd.DataFrame, col: str) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    metrics = df[col].apply(_version_metrics)
    out[f"{col}_exist"] = metrics.apply(lambda x: x[0])
    out[f"{col}_major"] = metrics.apply(lambda x: x[1])
    out[f"{col}_minor"] = metrics.apply(lambda x: x[2])
    out[f"{col}_patch"] = metrics.apply(lambda x: x[3])
    return out


def _license_tag_features(normalized_series: pd.Series) -> pd.DataFrame:
    out = pd.DataFrame(index=normalized_series.index)
    for tag in LICENSE_TAGS:
        out[f"licenses_{tag}_exist"] = normalized_series.apply(
            lambda lst, t=tag: 1 if any(t in item.lower() for item in lst) else 0
        )
    return out


def _dependency_ratio_features(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    deps = df.get(f"{COL_DEPENDENCIES}_count", pd.Series(0, index=df.index)).fillna(0)
    for col in _DEP_RATIO_COLS:
        count_col = f"{col}_count"
        if count_col in df.columns:
            cnt = df[count_col].fillna(0)
            out[f"{col}_ratio"] = np.where(deps == 0, 0, cnt / deps)
    return out


# ============================================================
# 진입점
# ============================================================

def featurize(df: pd.DataFrame) -> pd.DataFrame:
    """
    정규화된 DataFrame → 피쳐 DataFrame.
    출력 컬럼은 config/feature_schema.py OUTPUT_COLUMNS 순서로 고정.
    """
    parts = [df[ID_COLUMNS].reset_index(drop=True)]

    # 이름
    parts.append(_string_features(df, "name"))

    # 버전
    parts.append(_version_features(df, "version"))

    # 설명
    parts.append(_string_features(df, "summary_description"))

    # 키워드
    parts.append(_list_features(df, "keywords"))

    # 파일 (count만)
    parts.append(_list_features(df, "files", with_exist=False, with_avg=False))

    # 사람
    parts.append(_list_features(df, "author_names", with_count=False, with_avg=False))
    parts.append(_list_features(df, "people_names"))
    parts.append(_list_features(df, "people_emails", with_exist=False, with_count=False))

    # 라이선스 (SPDX 정규화 후 통계 + 태그)
    normalized_licenses = df["licenses"].apply(_normalize_licenses)
    lic_metrics = normalized_licenses.apply(
        lambda lst: (1 if lst else 0, len(lst),
                     sum(len(i) for i in lst) / len(lst) if lst else 0.0)
    )
    lic_df = pd.DataFrame({
        "licenses_exist":      lic_metrics.apply(lambda x: x[0]),
        "licenses_count":      lic_metrics.apply(lambda x: x[1]),
        "licenses_length_avg": lic_metrics.apply(lambda x: x[2]),
    }, index=df.index)
    parts.append(lic_df)
    parts.append(_license_tag_features(normalized_licenses))

    # 의존성
    for col in ["dependencies", "runtime", "development", "optional", "requirement"]:
        parts.append(_list_features(df, col, with_avg=(col == "dependencies")))
    parts.append(_dependency_ratio_features(pd.concat(parts, axis=1)))

    # URL
    for col in ["homepage", "download", "bug_tracking", "source_repository"]:
        parts.append(_string_features(df, col))

    out = pd.concat(parts, axis=1)

    # 스키마 컬럼 순서 강제
    for col in OUTPUT_COLUMNS:
        if col not in out.columns:
            out[col] = 0
    return out[OUTPUT_COLUMNS]
