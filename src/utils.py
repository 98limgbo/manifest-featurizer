# src/utils.py
# 2개 이상 모듈에서 호출되는 공통 함수만 포함

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd


# ============================================================
# I/O
# ============================================================

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=True)


def save_csv(df: pd.DataFrame, path: Path) -> None:
    ensure_dir(path.parent)
    df.to_csv(path, index=False, encoding="utf-8")


# ============================================================
# 공통 타입 변환
# ============================================================

def to_str(value: Any) -> str:
    """값을 문자열로 변환. None과 NaN은 빈 문자열 반환."""
    if value is None:
        return ""
    if isinstance(value, float):
        try:
            if pd.isna(value):
                return ""
        except Exception:
            pass
    return str(value).strip()


# ============================================================
# JSON 셀 파싱 (cleansing + normalization 공용)
# ============================================================

def try_parse_json(value: Any) -> Optional[Any]:
    """
    CSV 셀 값이 JSON list/dict 문자열이면 파싱해 반환.
    실패하거나 해당 형식이 아니면 None.
    """
    if value is None:
        return None
    if isinstance(value, float):
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass

    s = str(value).strip()
    if not s:
        return None
    if not ((s.startswith("[") and s.endswith("]")) or
            (s.startswith("{") and s.endswith("}"))):
        return None
    try:
        return json.loads(s)
    except Exception:
        return None
