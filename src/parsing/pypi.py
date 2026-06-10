# src/parsing/pypi.py
# PyPI PKG-INFO(Core Metadata) 파서
# 진입점: parse_pypi_pkg_info(text: str) -> dict

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

_RX_FOLD_WS  = re.compile(r"\n[ \t]+")
_RX_DESC_PIPE = re.compile(r"\n {7}\|")


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _split_headers_and_body(text: str) -> Tuple[List[str], str]:
    text  = _normalize_newlines(text)
    lines = text.split("\n")

    blank_idx: Optional[int] = None
    for i, line in enumerate(lines):
        if line.strip() == "":
            blank_idx = i
            break

    if blank_idx is None:
        return lines, ""
    return lines[:blank_idx], "\n".join(lines[blank_idx + 1 :])


def _parse_header_lines(header_lines: List[str]) -> Dict[str, List[str]]:
    fields: Dict[str, List[str]] = {}
    current_key: Optional[str] = None
    current_value_lines: List[str] = []

    def commit() -> None:
        nonlocal current_key, current_value_lines
        if current_key is None:
            return
        fields.setdefault(current_key, []).append("\n".join(current_value_lines))

    for line in header_lines:
        if line.startswith((" ", "\t")):
            if current_key is None:
                raise ValueError("Header continuation line found before any header field.")
            current_value_lines.append(line)
            continue

        commit()

        if ":" not in line:
            raise ValueError(f"Invalid header line (missing ':'): {line[:120]}")

        key, rest = line.split(":", 1)
        current_key = key.strip()
        current_value_lines = [rest.lstrip()]

    commit()
    return fields


def _unfold(raw_block: str) -> str:
    v = _normalize_newlines(raw_block)
    v = _RX_FOLD_WS.sub(" ", v)
    return v.strip()


def _decode_description(raw_block: str) -> str:
    v = _normalize_newlines(raw_block)
    v = _RX_DESC_PIPE.sub("\n", v)
    return v.rstrip()


def _first_value(fields: Dict[str, List[str]], key: str) -> Optional[str]:
    vs = fields.get(key)
    if not vs:
        return None
    v = _unfold(vs[0])
    return v if v else None


def _multi_use_list(fields: Dict[str, List[str]], key: str) -> Optional[List[str]]:
    vs = fields.get(key)
    if not vs:
        return None
    out = [_unfold(raw) for raw in vs if _unfold(raw)]
    return out if out else None


def _parse_keywords(fields: Dict[str, List[str]]) -> Optional[List[str]]:
    raw = _first_value(fields, "Keywords")
    if raw is None:
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts if parts else None


def _parse_project_urls(fields: Dict[str, List[str]]) -> Optional[List[List[str]]]:
    vs = fields.get("Project-URL")
    if not vs:
        return None
    out: List[List[str]] = []
    for raw_block in vs:
        v = _unfold(raw_block)
        if not v:
            continue
        if "," in v:
            label, url = v.split(",", 1)
            out.append([label.strip(), url.strip()])
        else:
            out.append([v.strip(), ""])
    return out if out else None


def parse_pypi_pkg_info(text: str) -> Dict[str, Any]:
    """
    PKG-INFO 텍스트 → PyPI 필드 dict 반환.
    files 필드는 PKG-INFO 표준에 없으므로 None으로 반환.
    (정규화 단계에서 [] 로 타입 통일)
    """
    header_lines, body = _split_headers_and_body(text)
    fields = _parse_header_lines(header_lines)

    if "Name" not in fields and "Metadata-Version" not in fields:
        raise ValueError("PKG-INFO does not look like core metadata (Name/Metadata-Version missing).")

    desc: Optional[str]
    if "Description" in fields and fields["Description"]:
        decoded = _decode_description(fields["Description"][0])
        desc = decoded if decoded.strip() else None
    else:
        b = _normalize_newlines(body).rstrip()
        desc = b if b.strip() else None

    return {
        "Name":               _first_value(fields, "Name"),
        "Version":            _first_value(fields, "Version"),
        "Summary":            _first_value(fields, "Summary"),
        "Description":        desc,
        "Keywords":           _parse_keywords(fields),
        "Author":             _first_value(fields, "Author"),
        "Author-email":       _first_value(fields, "Author-email"),
        "Maintainer":         _first_value(fields, "Maintainer"),
        "License":            _first_value(fields, "License"),
        "License-Expression": _first_value(fields, "License-Expression"),
        "Home-page":          _first_value(fields, "Home-page"),
        "Download-URL":       _first_value(fields, "Download-URL"),
        "Project-URL":        _parse_project_urls(fields),
        "Requires-Dist":      _multi_use_list(fields, "Requires-Dist"),
        "Provides-Extra":     _multi_use_list(fields, "Provides-Extra"),
        "files":              None,
    }
