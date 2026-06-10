# src/parsing/npm.py
# npm package.json 파서
# 진입점: parse_npm_package_json(text: str) -> dict

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple


def _as_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)


def _person_to_triplet(person: Any) -> List[str]:
    """
    npm people 필드(author, contributors, maintainers)를 [name, email, url]로 정규화.
    - object: {"name": ..., "email"?: ..., "url"?: ...}
    - string: "Name <email> (url)"
    """
    name = ""
    email = ""
    url = ""

    if isinstance(person, dict):
        name = _as_str(person.get("name"))
        email = _as_str(person.get("email"))
        url = _as_str(person.get("url"))
        return [name, email, url]

    s = _as_str(person).strip()
    if not s:
        return ["", "", ""]

    if "<" in s and ">" in s:
        left = s.find("<")
        right = s.find(">", left + 1)
        if right != -1:
            email = s[left + 1 : right].strip()

    if "(" in s and ")" in s:
        left = s.find("(")
        right = s.find(")", left + 1)
        if right != -1:
            url = s[left + 1 : right].strip()

    name_candidate = s
    if "<" in name_candidate and ">" in name_candidate:
        a = name_candidate.find("<")
        b = name_candidate.find(">", a + 1)
        if b != -1:
            name_candidate = (name_candidate[:a] + name_candidate[b + 1 :]).strip()
    if "(" in name_candidate and ")" in name_candidate:
        a = name_candidate.find("(")
        b = name_candidate.find(")", a + 1)
        if b != -1:
            name_candidate = (name_candidate[:a] + name_candidate[b + 1 :]).strip()

    name = name_candidate.strip()
    return [name, email, url]


def _map_to_pairs(obj: Any) -> Optional[List[List[str]]]:
    """
    dependencies 계열 dict(name→spec)를 [[name, spec], ...] 리스트로 변환.
    CSV 저장 안정성을 위해 pairs 형태로 유지.
    """
    if not isinstance(obj, dict) or not obj:
        return None

    pairs: List[List[str]] = []
    for k, v in obj.items():
        key = _as_str(k).strip()
        if not key:
            continue
        pairs.append([key, _as_str(v)])

    if not pairs:
        return None

    pairs.sort(key=lambda x: x[0])
    return pairs


def _bugs_to_raw(bugs: Any) -> Optional[Any]:
    if isinstance(bugs, str):
        s = bugs.strip()
        return s if s else None
    if isinstance(bugs, dict):
        out: List[List[str]] = []
        if "url" in bugs and _as_str(bugs.get("url")).strip():
            out.append(["url", _as_str(bugs.get("url"))])
        if "email" in bugs and _as_str(bugs.get("email")).strip():
            out.append(["email", _as_str(bugs.get("email"))])
        return out if out else None
    return None


def _repository_to_raw(repo: Any) -> Optional[Any]:
    if isinstance(repo, str):
        s = repo.strip()
        return s if s else None
    if isinstance(repo, dict):
        out: List[List[str]] = []
        for key in ("type", "url", "directory"):
            val = _as_str(repo.get(key)).strip()
            if val:
                out.append([key, val])
        return out if out else None
    return None


def _bundle_dependencies_value(pkg: Dict[str, Any]) -> Optional[List[str]]:
    """bundleDependencies/bundledDependencies 처리 (list 또는 boolean)."""
    val = pkg.get("bundleDependencies") or pkg.get("bundledDependencies")

    if isinstance(val, list):
        out = [_as_str(x).strip() for x in val if _as_str(x).strip()]
        return out if out else None

    if isinstance(val, bool):
        if not val:
            return None
        names: List[str] = []
        for key in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
            pairs = _map_to_pairs(pkg.get(key))
            if pairs:
                names.extend([p[0] for p in pairs if p and p[0]])
        uniq = sorted(set(names))
        return uniq if uniq else None

    return None


def _parse_files_field(pkg: Dict[str, Any]) -> Optional[List[str]]:
    val = pkg.get("files")
    if not isinstance(val, list):
        return None
    out = [_as_str(x).strip() for x in val if _as_str(x).strip()]
    return out if out else None


def parse_npm_package_json(text: str) -> Dict[str, Any]:
    """
    package.json 텍스트 → npm 필드 dict 반환.
    반환 값은 스칼라 또는 JSON 직렬화 가능한 리스트로만 구성.
    """
    try:
        pkg = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e

    if not isinstance(pkg, dict):
        raise ValueError("package.json root must be an object")

    name        = _as_str(pkg.get("name")).strip() or None
    version     = _as_str(pkg.get("version")).strip() or None
    description = _as_str(pkg.get("description")).strip() or None

    keywords_val = pkg.get("keywords")
    keywords: Optional[List[str]] = None
    if isinstance(keywords_val, list):
        ks = [_as_str(x).strip() for x in keywords_val if _as_str(x).strip()]
        keywords = ks if ks else None

    author_triplet = _person_to_triplet(pkg.get("author"))
    author_name  = author_triplet[0].strip() or None
    author_email = author_triplet[1].strip() or None

    contributors_val = pkg.get("contributors")
    contributors: Optional[List[List[str]]] = None
    if isinstance(contributors_val, list):
        cs = [_person_to_triplet(x) for x in contributors_val]
        cs = [t for t in cs if any(_as_str(v).strip() for v in t)]
        contributors = cs if cs else None

    maintainers_val = pkg.get("maintainers")
    maintainers: Optional[List[List[str]]] = None
    if isinstance(maintainers_val, list):
        ms = [_person_to_triplet(x) for x in maintainers_val]
        ms = [t for t in ms if any(_as_str(v).strip() for v in t)]
        maintainers = ms if ms else None

    license_val = pkg.get("license")
    license_str: Optional[str] = None
    if isinstance(license_val, str):
        s = license_val.strip()
        license_str = s if s else None
    elif isinstance(license_val, dict):
        s = _as_str(license_val.get("type")).strip()
        license_str = s if s else None

    licenses_val = pkg.get("licenses")
    licenses: Optional[List[str]] = None
    if isinstance(licenses_val, list):
        ls = [_as_str(item.get("type")).strip() for item in licenses_val
              if isinstance(item, dict) and _as_str(item.get("type")).strip()]
        licenses = ls if ls else None

    return {
        "name":                 name,
        "version":              version,
        "description":          description,
        "keywords":             keywords,
        "author":               author_name,
        "author.email":         author_email,
        "contributors":         contributors,
        "maintainers":          maintainers,
        "license":              license_str,
        "licenses":             licenses,
        "homepage":             _as_str(pkg.get("homepage")).strip() or None,
        "bugs":                 _bugs_to_raw(pkg.get("bugs")),
        "repository":           _repository_to_raw(pkg.get("repository")),
        "dependencies":         _map_to_pairs(pkg.get("dependencies")),
        "devDependencies":      _map_to_pairs(pkg.get("devDependencies")),
        "optionalDependencies": _map_to_pairs(pkg.get("optionalDependencies")),
        "peerDependencies":     _map_to_pairs(pkg.get("peerDependencies")),
        "bundleDependencies":   _bundle_dependencies_value(pkg),
        "files":                _parse_files_field(pkg),
    }
