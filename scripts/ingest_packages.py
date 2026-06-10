# scripts/ingest_packages.py
# 외부 경로의 압축 파일에서 매니페스트를 추출해 data/00_manifest에 저장
# 실행: python -m scripts.ingest_packages <source_dir> <registry> <label> [--source new]

from __future__ import annotations

import argparse
import re
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from tqdm import tqdm

from config.paths import MANIFEST_DIR

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"


# ============================================================
# 아카이브 추출 함수 (레지스트리별)
# ============================================================

def _read_from_tgz(archive_path: Path, manifest_paths: List[str]) -> Optional[bytes]:
    """tgz에서 manifest_paths 중 첫 번째로 존재하는 파일의 내용을 반환."""
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            for mp in manifest_paths:
                try:
                    member = tar.getmember(mp)
                    f = tar.extractfile(member)
                    if f:
                        return f.read()
                except KeyError:
                    continue
    except Exception:
        pass
    return None


def _read_from_zip(archive_path: Path, manifest_paths: List[str]) -> Optional[bytes]:
    """zip/whl에서 manifest_paths 중 첫 번째로 존재하는 파일의 내용을 반환."""
    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            names = zf.namelist()
            for mp in manifest_paths:
                # wheel 등은 경로 prefix가 붙으므로 suffix 매칭
                matched = next((n for n in names if n == mp or n.endswith("/" + mp)), None)
                if matched:
                    return zf.read(matched)
    except Exception:
        pass
    return None


# ============================================================
# 레지스트리별 설정 (새 레지스트리 추가 시 여기만 수정)
# ============================================================

_REGISTRY_CONFIG: Dict[str, Dict] = {
    "npm": {
        "ext": ".tgz",
        "manifest_paths": ["package/package.json", "package.json"],
        "extractor": _read_from_tgz,
        "manifest_filename": "package.json",
    },
    # "pypi": {
    #     "ext": ".whl",
    #     "manifest_paths": ["PKG-INFO"],
    #     "extractor": _read_from_zip,
    #     "manifest_filename": "PKG-INFO",
    # },
}


# ============================================================
# 파일명 파싱
# ============================================================

def _parse_archive_name(filename: str, ext: str) -> Tuple[str, str]:
    """
    '{name}-{version}{ext}' → (name, version)
    버전은 숫자로 시작하는 마지막 하이픈 이후 부분으로 판단.
    파싱 실패 시 (stem, "") 반환.
    """
    stem = filename[: -len(ext)] if filename.endswith(ext) else filename
    match = re.search(r"-(\d[^-]*)$", stem)
    if match:
        version = match.group(1)
        name = stem[: match.start()]
        return name, version
    return stem, ""


def _make_folder_name(name: str, version: str) -> str:
    """
    패키지명·버전 → 폴더명 (loader.py 규칙과 동일)
    @scope/name → @scope@@name##{version}
    name        → name##{version}
    """
    if name.startswith("@") and "/" in name:
        scope, pkg = name.split("/", 1)
        return f"{scope}@@{pkg}##{version}"
    return f"{name}##{version}"


# ============================================================
# 핵심 처리 함수
# ============================================================

def _process_archive(
    archive_path: Path,
    manifest_paths: List[str],
    extractor_fn: Callable,
    manifest_filename: str,
    ext: str,
    dest_label_dir: Path,
) -> Optional[str]:
    """
    아카이브 하나를 처리해 매니페스트를 목적지에 저장.
    반환: 실패 시 오류 메시지, 성공 시 None.
    """
    name, version = _parse_archive_name(archive_path.name, ext)
    if not name:
        return "파일명 파싱 실패"

    folder_name = _make_folder_name(name, version)
    dest_dir = dest_label_dir / folder_name
    dest_file = dest_dir / manifest_filename

    # 이미 존재하면 스킵
    if dest_file.exists():
        return None

    content = extractor_fn(archive_path, manifest_paths)
    if content is None:
        return "매니페스트 추출 실패"

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file.write_bytes(content)
    return None


def ingest_registry(
    source_dir: Path,
    registry: str,
    label: str,
    source: str = "new",
    dest_dir: Path = MANIFEST_DIR,
) -> None:
    """
    source_dir의 아카이브 파일들을 순회해 매니페스트를 dest_dir에 저장.

    dest_dir/{source}/{registry}/{label}/{name}##{version}/{manifest_filename}
    """
    cfg = _REGISTRY_CONFIG.get(registry)
    if cfg is None:
        raise ValueError(f"지원하지 않는 레지스트리: {registry}. _REGISTRY_CONFIG에 추가 필요.")

    ext             = cfg["ext"]
    manifest_paths  = cfg["manifest_paths"]
    extractor_fn    = cfg["extractor"]
    manifest_file   = cfg["manifest_filename"]

    dest_label_dir = dest_dir / source / registry / label
    archives = sorted(source_dir.glob(f"*{ext}"))

    if not archives:
        print(f"  {ext} 파일 없음: {source_dir}")
        return

    failed: List[str] = []
    skipped = 0
    success = 0

    for archive_path in tqdm(archives, desc=f"{registry}/{label}"):
        # 스킵 여부 사전 체크 (tqdm 루프 안에서 _process_archive가 판단)
        name, version = _parse_archive_name(archive_path.name, ext)
        folder_name = _make_folder_name(name, version)
        if (dest_label_dir / folder_name / manifest_file).exists():
            skipped += 1
            continue

        error = _process_archive(
            archive_path, manifest_paths, extractor_fn, manifest_file, ext, dest_label_dir
        )
        if error:
            failed.append(f"{archive_path.name}: {error}")
        else:
            success += 1

    # 결과 출력
    total = len(archives)
    print(f"\n  완료: 총={total}  성공={success}  스킵={skipped}  실패={len(failed)}")

    # 실패 목록 저장
    if failed:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = LOG_DIR / f"failed_{registry}_{label}_{timestamp}.txt"
        LOG_DIR.mkdir(exist_ok=True)
        log_path.write_text("\n".join(failed), encoding="utf-8")
        print(f"  실패 목록 저장: {log_path}")


# ============================================================
# 진입점
# ============================================================

def run() -> None:
    parser = argparse.ArgumentParser(
        description="외부 경로의 패키지 아카이브에서 매니페스트를 추출해 data/00_manifest에 저장"
    )
    parser.add_argument("source_dir", type=Path, help="아카이브 파일이 있는 폴더 경로")
    parser.add_argument("registry",   type=str,  help="레지스트리 이름 (npm / pypi / rubygems)")
    parser.add_argument("label",      type=str,  help="레이블 (malicious / benign / spam 등)")
    parser.add_argument("--source",   type=str,  default="new",
                        help="수집 시점 태그 (기본값: new)")
    parser.add_argument("--dest",     type=Path, default=MANIFEST_DIR,
                        help="저장 루트 경로 (기본값: data/00_manifest)")
    args = parser.parse_args()

    print(f"=== ingest_packages ===")
    print(f"  source_dir : {args.source_dir}")
    print(f"  registry   : {args.registry}")
    print(f"  label      : {args.label}")
    print(f"  source     : {args.source}")
    print(f"  dest       : {args.dest}")

    ingest_registry(
        source_dir=args.source_dir,
        registry=args.registry,
        label=args.label,
        source=args.source,
        dest_dir=args.dest,
    )


if __name__ == "__main__":
    run()
