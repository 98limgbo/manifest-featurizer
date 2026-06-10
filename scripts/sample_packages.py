# scripts/sample_packages.py
# 03_normalized CSV에서 조건에 맞는 패키지를 label별 1개씩 샘플링해
# data/sample/에 매니페스트 파일을 복사
# 실행: python -m scripts.sample_packages [--seed N]

from __future__ import annotations

import argparse
import shutil

import pandas as pd

from config.paths import MANIFEST_DIR, DATA_DIR, normalized_path

_REGISTRIES = ["npm", "pypi", "rubygems"]
_REGISTRY_MANIFEST = {
    "npm":      "package.json",
    "pypi":     "PKG-INFO",
    "rubygems": "metadata",
}
SAMPLE_DIR = DATA_DIR / "sample"


def _make_folder_name(name: str, version: str) -> str:
    """패키지명·버전 → 폴더명 (loader.py 규칙과 동일)"""
    if name.startswith("@") and "/" in name:
        scope, pkg = name.split("/", 1)
        return f"{scope}@@{pkg}##{version}"
    return f"{name}##{version}"


def _manifest_path(source: str, registry: str, label: str,
                   name: str, version: str) -> str:
    folder = _make_folder_name(name, version)
    manifest_file = _REGISTRY_MANIFEST[registry]
    return MANIFEST_DIR / source / registry / label / folder / manifest_file


def sample_packages(seed: int = 42) -> None:
    copied = 0

    for registry in _REGISTRIES:
        path = normalized_path(registry)
        if not path.exists():
            print(f"[SKIP] {registry}: 파일 없음")
            continue

        df = pd.read_csv(path, low_memory=False)

        # 조건 필터링
        # 1) licenses에 "mit" 포함
        # 2) 매니페스트에서 파싱한 name, version이 비어있지 않음
        mask = (
            df["licenses"].str.lower().str.contains("mit", na=False)
            & df["name"].notna() & (df["name"].str.strip() != "")
            & df["version"].notna() & (df["version"].str.strip() != "")
        )
        filtered = df[mask]

        if filtered.empty:
            print(f"[SKIP] {registry}: 조건에 맞는 패키지 없음")
            continue

        # label별 1개 랜덤 샘플
        samples = filtered.groupby("label").sample(n=1, random_state=seed)

        for _, row in samples.iterrows():
            source   = row["source"]
            label    = row["label"]
            name     = row["name"]
            version  = row["version"]
            pkg_id   = row["id"]

            src_path = _manifest_path(source, registry, label, name, version)
            if not src_path.exists():
                print(f"[MISS] {pkg_id}: 매니페스트 파일 없음 ({src_path})")
                continue

            # 목적지: data/sample/{source}/{registry}/{label}/{folder}/{manifest}
            dst_path = SAMPLE_DIR / src_path.relative_to(MANIFEST_DIR)
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
            print(f"[OK]   {pkg_id}")
            copied += 1

    print(f"\n완료: {copied}개 복사 → {SAMPLE_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42, help="랜덤 시드 (기본값: 42)")
    args = parser.parse_args()
    sample_packages(seed=args.seed)
