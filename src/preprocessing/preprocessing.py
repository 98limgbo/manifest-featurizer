# src/preprocessing/preprocessing.py
# 피쳐 전처리 — 진입점: preprocess(df) -> pd.DataFrame
# 변환 대상 피쳐는 config/preprocess_schema.py에서 import

from __future__ import annotations

import numpy as np
import pandas as pd

from config.preprocess_schema import LOG_TRANSFORM_FEATURES


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """
    피쳐 DataFrame에 전처리 변환 적용.
    - LOG_TRANSFORM_FEATURES: np.log1p 적용
    존재하지 않는 컬럼은 무시.
    """
    out = df.copy()
    for col in LOG_TRANSFORM_FEATURES:
        if col in out.columns:
            out[col] = np.log1p(pd.to_numeric(out[col], errors="coerce").fillna(0))
    return out
