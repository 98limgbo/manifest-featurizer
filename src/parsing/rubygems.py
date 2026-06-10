# src/parsing/rubygems.py
# RubyGems metadata(YAML; Gem::Specification) 파서
# 진입점: parse_rubygems_metadata(text: str) -> dict

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError as e:
    raise ImportError("PyYAML이 필요합니다. `pip install pyyaml`로 설치하세요.") from e


class _RubyYamlLoader(yaml.SafeLoader):
    """RubyGems metadata의 !ruby/object:* 태그를 안전하게 처리."""


def _construct_unknown(loader: yaml.SafeLoader, tag_suffix: str, node: yaml.Node) -> Any:
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    return loader.construct_scalar(node)


_RubyYamlLoader.add_multi_constructor("", _construct_unknown)


def _as_str(v: Any) -> str:
    if v is None:
        return ""
    return v if isinstance(v, str) else str(v)


def _as_optional_str(v: Any) -> Optional[str]:
    s = _as_str(v).strip()
    return s if s else None


def _as_str_list_optional(v: Any) -> Optional[List[str]]:
    if v is None:
        return None
    if isinstance(v, list):
        out = [_as_str(x).strip() for x in v if _as_str(x).strip()]
        return out if out else None
    s = _as_str(v).strip()
    return [s] if s else None


def _extract_version_like(v: Any) -> Optional[str]:
    """Gem::Version 객체를 문자열로 변환."""
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        return s if s else None
    if isinstance(v, dict):
        if "version" in v:
            s = _as_str(v.get("version")).strip()
            return s if s else None
        if "segments" in v and isinstance(v["segments"], list):
            segs = [str(x) for x in v["segments"] if _as_str(x).strip()]
            s = ".".join(segs).strip()
            return s if s else None
    s = _as_str(v).strip()
    return s if s else None


def _extract_requirement_strings(req_obj: Any) -> Optional[List[str]]:
    """Gem::Requirement를 문자열 리스트로 변환."""
    if req_obj is None:
        return None
    if isinstance(req_obj, str):
        s = req_obj.strip()
        return [s] if s else None
    if isinstance(req_obj, list):
        out: List[str] = []
        for it in req_obj:
            if isinstance(it, (list, tuple)) and len(it) >= 2:
                op  = _as_str(it[0]).strip()
                ver = _extract_version_like(it[1]) or ""
                s   = f"{op} {ver}".strip()
                if s:
                    out.append(s)
            else:
                s = _as_str(it).strip()
                if s:
                    out.append(s)
        return out if out else None
    if isinstance(req_obj, dict):
        if "requirements" in req_obj:
            return _extract_requirement_strings(req_obj.get("requirements"))
        if "requirement" in req_obj:
            return _extract_requirement_strings(req_obj.get("requirement"))
    s = _as_str(req_obj).strip()
    return [s] if s else None


def _normalize_dep_type(dep_type: Any) -> str:
    t = _as_str(dep_type).strip().lower()
    return t[1:] if t.startswith(":") else t


def _parse_dependencies(spec: Dict[str, Any]) -> Tuple[Optional[List[List[Any]]], Optional[List[List[Any]]]]:
    """
    spec["dependencies"] → (runtime, development)
    형태: [[dep_name, [req_str, ...]], ...]
    """
    deps = spec.get("dependencies")
    if not isinstance(deps, list) or not deps:
        return None, None

    runtime:     List[List[Any]] = []
    development: List[List[Any]] = []

    for dep in deps:
        if not isinstance(dep, dict):
            continue
        dep_name = _as_str(dep.get("name")).strip()
        if not dep_name:
            continue
        dep_type = _normalize_dep_type(dep.get("type"))
        req_list = _extract_requirement_strings(dep.get("requirement"))
        pair: List[Any] = [dep_name, req_list if req_list is not None else []]

        if dep_type == "runtime":
            runtime.append(pair)
        elif dep_type == "development":
            development.append(pair)

    if runtime:
        runtime.sort(key=lambda x: _as_str(x[0]))
    if development:
        development.sort(key=lambda x: _as_str(x[0]))

    return (runtime or None), (development or None)


def _parse_files_field(spec: Dict[str, Any]) -> Optional[List[str]]:
    v = spec.get("files")
    if v is None:
        return None
    if isinstance(v, list):
        out = [_as_str(x).strip() for x in v if _as_str(x).strip()]
        return out if out else None
    s = _as_str(v).strip()
    return [s] if s else None


def parse_rubygems_metadata(text: str) -> Dict[str, Any]:
    """
    RubyGems metadata YAML 텍스트 → RubyGems 필드 dict 반환.
    """
    try:
        spec = yaml.load(text, Loader=_RubyYamlLoader)
    except Exception as e:
        raise ValueError(f"Invalid YAML: {e}") from e

    if not isinstance(spec, dict):
        raise ValueError("RubyGems metadata root must be a mapping.")

    md = spec.get("metadata", {})
    if not isinstance(md, dict):
        md = {}

    runtime_deps, dev_deps = _parse_dependencies(spec)

    return {
        "name":                      _as_optional_str(spec.get("name")),
        "version":                   _extract_version_like(spec.get("version")),
        "summary":                   _as_optional_str(spec.get("summary")),
        "description":               _as_optional_str(spec.get("description")),
        "authors":                   _as_str_list_optional(spec.get("authors")),
        "email":                     _as_str_list_optional(spec.get("email")),
        "license":                   _as_optional_str(spec.get("license")),
        "licenses":                  _as_str_list_optional(spec.get("licenses")),
        "homepage":                  _as_optional_str(spec.get("homepage")),
        "metadata.homepage_uri":     _as_optional_str(md.get("homepage_uri")),
        "metadata.bug_tracker_uri":  _as_optional_str(md.get("bug_tracker_uri")),
        "metadata.source_code_uri":  _as_optional_str(md.get("source_code_uri")),
        "dependencies.runtime":      runtime_deps,
        "dependencies.development":  dev_deps,
        "files":                     _parse_files_field(spec),
    }
