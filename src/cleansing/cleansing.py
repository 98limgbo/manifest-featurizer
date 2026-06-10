# src/cleansing/cleansing.py
# 정제 로직 — 진입점: cleanse(df, registry) -> (pd.DataFrame, dict)
# 규칙은 config/registry_schema.py에서 import

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Set, Tuple

import pandas as pd

from config.registry_schema import (
    COL_ID, COL_SOURCE, COL_REGISTRY, COL_LABEL,
    NPM_PLACEHOLDER_EXACT, NPM_PLACEHOLDER_PREFIX,
    PYPI_PLACEHOLDER_EXACT, PYPI_PLACEHOLDER_PREFIX,
    RUBYGEMS_PLACEHOLDER_EXACT, RUBYGEMS_PLACEHOLDER_PREFIX,
)
from src.utils import try_parse_json

# 정제하지 않는 식별 컬럼
_META_COLS = {COL_ID, COL_SOURCE, COL_REGISTRY, COL_LABEL}

# 레지스트리별 placeholder 규칙
_PLACEHOLDER_RULES: Dict[str, Tuple[Set[str], Tuple[str, ...]]] = {
    "npm":      (set(NPM_PLACEHOLDER_EXACT),      tuple(NPM_PLACEHOLDER_PREFIX)),
    "pypi":     (set(PYPI_PLACEHOLDER_EXACT),     tuple(PYPI_PLACEHOLDER_PREFIX)),
    "rubygems": (set(RUBYGEMS_PLACEHOLDER_EXACT), tuple(RUBYGEMS_PLACEHOLDER_PREFIX)),
}


# ============================================================
# 통계
# ============================================================

@dataclass
class CleanseStats:
    rows: int = 0
    cols_processed: int = 0
    scalar_placeholders_cleared: int = 0
    list_elements_removed: int = 0
    list_elements_deduped: int = 0
    dict_values_cleaned: int = 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


# ============================================================
# 내부 헬퍼
# ============================================================

def _is_placeholder(s: str, exact: Set[str], prefix: Tuple[str, ...]) -> bool:
    if s in exact:
        return True
    return any(s.startswith(p) for p in prefix)


def _clean_scalar(s: str, exact: Set[str], prefix: Tuple[str, ...], stats: CleanseStats) -> str:
    s = s.strip()
    if not s:
        return ""
    if _is_placeholder(s, exact, prefix):
        stats.scalar_placeholders_cleared += 1
        return ""
    return s


def _clean_list(
    arr: List[Any],
    exact: Set[str],
    prefix: Tuple[str, ...],
    stats: CleanseStats,
) -> List[Any]:
    """
    리스트 요소 정제 (구조 보존):
    - None 제거
    - 중첩 리스트: 재귀 정제 후 빈 리스트는 제거
    - 중첩 dict: shallow 정제
    - 스칼라: strip + placeholder 제거
    순서 유지, 중복 제거
    """
    seen: List[str] = []
    out: List[Any] = []
    original_len = len(arr)
    local_deduped = 0

    for el in arr:
        if el is None:
            continue

        if isinstance(el, list):
            nested = _clean_list(el, exact, prefix, stats)
            if nested:
                out.append(nested)
            continue

        if isinstance(el, dict):
            out.append(_clean_dict_shallow(el, exact, prefix, stats))
            continue

        s = _clean_scalar(str(el), exact, prefix, stats)
        if not s:
            continue

        try:
            sig = json.dumps(s, ensure_ascii=False)
        except Exception:
            sig = s

        if sig in seen:
            stats.list_elements_deduped += 1
            local_deduped += 1
            continue

        seen.append(sig)
        out.append(s)

    stats.list_elements_removed += original_len - len(out) - local_deduped
    return out


def _clean_dict_shallow(
    obj: Dict[str, Any],
    exact: Set[str],
    prefix: Tuple[str, ...],
    stats: CleanseStats,
) -> Dict[str, Any]:
    """dict 값이 문자열인 경우만 shallow 정제 (구조 변경 없음)."""
    out = {}
    for k, v in obj.items():
        if isinstance(v, str):
            cleaned = _clean_scalar(v, exact, prefix, stats)
            if cleaned != v:
                stats.dict_values_cleaned += 1
            out[k] = cleaned
        else:
            out[k] = v
    return out


def _cleanse_cell(
    value: Any,
    exact: Set[str],
    prefix: Tuple[str, ...],
    stats: CleanseStats,
) -> str:
    """셀 하나 정제 → 항상 문자열 반환."""
    if value is None:
        return ""
    if isinstance(value, float):
        try:
            if pd.isna(value):
                return ""
        except Exception:
            pass

    parsed = try_parse_json(value)

    if isinstance(parsed, list):
        cleaned = _clean_list(parsed, exact, prefix, stats)
        return json.dumps(cleaned, ensure_ascii=False)

    if isinstance(parsed, dict):
        cleaned_dict = _clean_dict_shallow(parsed, exact, prefix, stats)
        return json.dumps(cleaned_dict, ensure_ascii=False)

    return _clean_scalar(str(value), exact, prefix, stats)


# ============================================================
# 진입점
# ============================================================

def cleanse(df: pd.DataFrame, registry: str) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    레지스트리별 placeholder 규칙을 적용해 DataFrame 정제.
    식별 컬럼(id, source, registry, label)은 정제하지 않음.

    반환: (정제된 DataFrame, 통계 dict)
    """
    exact, prefix = _PLACEHOLDER_RULES.get(registry, (set(), tuple()))
    stats = CleanseStats(rows=len(df), cols_processed=len(df.columns) - len(_META_COLS))

    out = df.copy()
    for col in out.columns:
        if col in _META_COLS:
            continue
        out[col] = out[col].apply(lambda v: _cleanse_cell(v, exact, prefix, stats))

    return out, stats.to_dict()
