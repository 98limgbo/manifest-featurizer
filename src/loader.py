# src/loader.py
# 00_manifest 폴더 순회 + 경로에서 메타데이터 추출 + ID 생성 + 파서 디스패치
# 새 레지스트리 추가 시: _REGISTRY_CONFIG에 항목 추가 + 파서 import 추가

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from tqdm import tqdm

from src.parsing.npm import parse_npm_package_json
from src.parsing.pypi import parse_pypi_pkg_info
from src.parsing.rubygems import parse_rubygems_metadata
from config.paths import MANIFEST_DIR


# ============================================================
# 레지스트리별 설정 (새 레지스트리 추가 시 여기만 수정)
# ============================================================
_REGISTRY_CONFIG: Dict[str, Dict[str, Any]] = {
    "npm":      {"manifest_file": "package.json", "parser": parse_npm_package_json},
    "pypi":     {"manifest_file": "PKG-INFO",     "parser": parse_pypi_pkg_info},
    "rubygems": {"manifest_file": "metadata",     "parser": parse_rubygems_metadata},
}


# ============================================================
# 폴더명 파싱: {scope}@@{name}##{version} 또는 {name}##{version}
# ============================================================
def _parse_folder_name(folder_name: str) -> Tuple[str, str]:
    """
    반환: (package_name, version)
    npm 스코프 패키지: "@scope@@name##version" → ("@scope/name", "version")
    일반 패키지:       "name##version"          → ("name", "version")
    """
    if "##" not in folder_name:
        return folder_name, ""

    name_raw, version = folder_name.rsplit("##", 1)

    if "@@" in name_raw:
        scope, name_part = name_raw.split("@@", 1)
        package_name = f"{scope}/{name_part}"
    else:
        package_name = name_raw

    return package_name, version


def _make_id(source: str, registry: str, label: str, name: str, version: str) -> str:
    return f"{source}::{registry}::{label}::{name}::{version}"


# ============================================================
# 단일 패키지 로드
# ============================================================
def _load_package(
    pkg_dir: Path,
    source: str,
    registry: str,
    label: str,
    manifest_file: str,
    parser: Any,
) -> Optional[Dict[str, Any]]:
    manifest_path = pkg_dir / manifest_file
    if not manifest_path.exists():
        return None

    try:
        text = manifest_path.read_text(encoding="utf-8", errors="replace")
        fields = parser(text)
    except Exception:
        return None

    package_name, version = _parse_folder_name(pkg_dir.name)

    row = {
        "id":       _make_id(source, registry, label, package_name, version),
        "source":   source,
        "registry": registry,
        "label":    label,
    }
    row.update(fields)
    return row


# ============================================================
# 레지스트리 전체 로드 (진입점)
# ============================================================
def load_registry(registry: str, manifest_dir: Path = MANIFEST_DIR) -> pd.DataFrame:
    """
    00_manifest/{source}/{registry}/{label}/ 구조를 순회해
    해당 레지스트리의 모든 패키지를 파싱하고 DataFrame으로 반환.
    """
    cfg = _REGISTRY_CONFIG.get(registry)
    if cfg is None:
        raise ValueError(f"지원하지 않는 레지스트리: {registry}. _REGISTRY_CONFIG에 추가 필요.")

    manifest_file: str = cfg["manifest_file"]
    parser = cfg["parser"]

    rows: List[Dict[str, Any]] = []

    registry_root = manifest_dir
    # source 폴더 순회 (old, new, ...)
    for source_dir in sorted(registry_root.iterdir()):
        if not source_dir.is_dir():
            continue
        source = source_dir.name

        reg_dir = source_dir / registry
        if not reg_dir.exists():
            continue

        # label 폴더 순회 (malicious, benign, spam, ...)
        for label_dir in sorted(reg_dir.iterdir()):
            if not label_dir.is_dir():
                continue
            label = label_dir.name

            # 패키지 폴더 순회
            pkg_dirs = sorted(label_dir.iterdir())
            for pkg_dir in tqdm(pkg_dirs, desc=f"{source}/{registry}/{label}", leave=False):
                if not pkg_dir.is_dir():
                    continue

                row = _load_package(
                    pkg_dir=pkg_dir,
                    source=source,
                    registry=registry,
                    label=label,
                    manifest_file=manifest_file,
                    parser=parser,
                )
                if row is not None:
                    rows.append(row)

    return pd.DataFrame(rows)
