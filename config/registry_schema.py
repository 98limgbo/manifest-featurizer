# config/registry_schema.py
# WHAT: 레지스트리별 원본 필드명 → 통합 필드명 매핑 + placeholder 제거 규칙
# HOW(로직)는 src/normalization/normalization.py, src/cleansing/cleansing.py 참고

from __future__ import annotations
from typing import Dict, List, Tuple


# ============================================================
# 통합 필드명 (정규화 후 기준) — 모든 레지스트리 공통
# ============================================================

# 메타데이터 식별 컬럼 (loader.py에서 경로 기반으로 자동 생성)
COL_ID       = "id"        # source::registry::label::name::version
COL_SOURCE   = "source"    # old / new
COL_REGISTRY = "registry"  # npm / pypi / rubygems
COL_LABEL    = "label"     # malicious / benign / spam 등

# 측정 컬럼 (loader.py에서 파싱 시 측정)
COL_DURATION = "duration"  # 파일 읽기 + 파싱 소요 시간 (초)

# 일반 정보
COL_NAME                = "name"
COL_VERSION             = "version"
COL_SUMMARY_DESCRIPTION = "summary_description"   # summary + "\n\n" + description
COL_KEYWORDS            = "keywords"               # list
COL_FILES               = "files"                  # list

# 사람
COL_AUTHOR_NAMES                  = "author_names"                   # list
COL_AUTHOR_EMAILS                 = "author_emails"                  # list
COL_CONTRIB_MAINT_NAMES           = "contributors_maintainer_names"  # list
COL_CONTRIB_MAINT_EMAILS          = "contributors_maintainer_emails" # list
COL_PEOPLE_NAMES                  = "people_names"                   # list (author + contrib/maint 통합)
COL_PEOPLE_EMAILS                 = "people_emails"                  # list (author + contrib/maint 통합)

# 라이선스
COL_LICENSES = "licenses"  # list

# 의존성
COL_DEPENDENCIES = "dependencies"  # list — npm:dependencies, pypi:Requires-Dist(non-optional)
COL_RUNTIME      = "runtime"       # list — rubygems:dependencies.runtime
COL_DEVELOPMENT  = "development"   # list — npm:devDependencies, rubygems:dependencies.development
COL_OPTIONAL     = "optional"      # list — npm:optionalDependencies, pypi:optional(Provides-Extra 기반)
COL_REQUIREMENT  = "requirement"   # list — npm:peerDependencies

# URL
COL_HOMEPAGE          = "homepage"           # str
COL_DOWNLOAD          = "download"           # str
COL_BUG_TRACKING      = "bug_tracking"       # str
COL_SOURCE_REPOSITORY = "source_repository"  # str


# ============================================================
# 정규화 출력 컬럼 순서
# ============================================================
NORMALIZED_COLUMNS: List[str] = [
    COL_ID, COL_SOURCE, COL_REGISTRY, COL_LABEL, 
    COL_NAME, COL_VERSION, COL_SUMMARY_DESCRIPTION, COL_KEYWORDS, COL_FILES, COL_DURATION,
    COL_AUTHOR_NAMES, COL_AUTHOR_EMAILS,
    COL_CONTRIB_MAINT_NAMES, COL_CONTRIB_MAINT_EMAILS,
    COL_PEOPLE_NAMES, COL_PEOPLE_EMAILS,
    COL_LICENSES,
    COL_DEPENDENCIES, COL_RUNTIME, COL_DEVELOPMENT, COL_OPTIONAL, COL_REQUIREMENT,
    COL_HOMEPAGE, COL_DOWNLOAD, COL_BUG_TRACKING, COL_SOURCE_REPOSITORY,
]


# ============================================================
# npm 원본 필드명 → 통합 필드명 매핑
# ============================================================
# 파서 출력(parse_npm_package_json) 기준
# bundleDependencies: 탐지 목적상 불필요 → 제외

NPM_RAW_NAME                  = "name"
NPM_RAW_VERSION               = "version"
NPM_RAW_DESCRIPTION           = "description"       # → summary_description
NPM_RAW_KEYWORDS              = "keywords"           # list
NPM_RAW_FILES                 = "files"              # list
NPM_RAW_AUTHOR                = "author"             # str → author_names
NPM_RAW_AUTHOR_EMAIL          = "author.email"       # str → author_emails
NPM_RAW_CONTRIBUTORS          = "contributors"       # [[name,email,url],...] → contrib_maint_names/emails
NPM_RAW_MAINTAINERS           = "maintainers"        # [[name,email,url],...] → contrib_maint_names/emails
NPM_RAW_LICENSE               = "license"            # str → licenses
NPM_RAW_LICENSES              = "licenses"           # list → licenses (deprecated, 병합)
NPM_RAW_HOMEPAGE              = "homepage"           # str → homepage
NPM_RAW_BUGS                  = "bugs"               # str or [[key,val],...] → bug_tracking
NPM_RAW_REPOSITORY            = "repository"         # str or [[key,val],...] → source_repository
NPM_RAW_DEPENDENCIES          = "dependencies"       # [[name,spec],...] → dependencies (name만 추출)
NPM_RAW_DEV_DEPENDENCIES      = "devDependencies"    # [[name,spec],...] → development
NPM_RAW_OPTIONAL_DEPENDENCIES = "optionalDependencies"  # [[name,spec],...] → optional
NPM_RAW_PEER_DEPENDENCIES     = "peerDependencies"   # [[name,spec],...] → requirement
# bundleDependencies → 제외


# ============================================================
# PyPI 원본 필드명 → 통합 필드명 매핑
# ============================================================
# 파서 출력(parse_pypi_pkg_info) 기준

PYPI_RAW_NAME               = "Name"
PYPI_RAW_VERSION            = "Version"
PYPI_RAW_SUMMARY            = "Summary"             # → summary_description (앞부분)
PYPI_RAW_DESCRIPTION        = "Description"         # → summary_description (뒷부분)
PYPI_RAW_KEYWORDS           = "Keywords"            # list
PYPI_RAW_AUTHOR             = "Author"              # str → author_names
PYPI_RAW_AUTHOR_EMAIL       = "Author-email"        # str → author_emails
PYPI_RAW_MAINTAINER         = "Maintainer"          # str → contributors_maintainer_names
PYPI_RAW_LICENSE            = "License"             # str → licenses
PYPI_RAW_LICENSE_EXPRESSION = "License-Expression"  # str → licenses (병합)
PYPI_RAW_HOME_PAGE          = "Home-page"           # str → homepage
PYPI_RAW_DOWNLOAD_URL       = "Download-URL"        # str → download
PYPI_RAW_PROJECT_URL        = "Project-URL"         # [[label,url],...] → 패턴 매칭으로 각 URL 컬럼
PYPI_RAW_REQUIRES_DIST      = "Requires-Dist"       # list → dependencies (non-optional) + optional
PYPI_RAW_PROVIDES_EXTRA     = "Provides-Extra"      # list → optional 추출에 활용 후 버림
PYPI_RAW_FILES              = "files"               # None → [] (정규화 단계에서 타입 통일)

# PyPI Project-URL label 패턴 매칭 (대소문자 무시, 공백/하이픈/언더스코어 제거 후 substring)
PYPI_PROJECT_URL_HOMEPAGE_PATTERNS:     List[str] = ["homepage"]
PYPI_PROJECT_URL_DOWNLOAD_PATTERNS:     List[str] = ["download"]
PYPI_PROJECT_URL_BUG_TRACKING_PATTERNS: List[str] = ["bugs", "issue", "tracker", "issuetracker", "bugtracker"]
PYPI_PROJECT_URL_SOURCE_REPO_PATTERNS:  List[str] = ["repository", "sourcecode", "github"]


# ============================================================
# RubyGems 원본 필드명 → 통합 필드명 매핑
# ============================================================
# 파서 출력(parse_rubygems_metadata) 기준
# metadata (raw dict): 개별 필드가 이미 추출됐으므로 제외

RUBYGEMS_RAW_NAME              = "name"
RUBYGEMS_RAW_VERSION           = "version"
RUBYGEMS_RAW_SUMMARY           = "summary"              # → summary_description (앞부분)
RUBYGEMS_RAW_DESCRIPTION       = "description"          # → summary_description (뒷부분)
RUBYGEMS_RAW_AUTHORS           = "authors"              # list → author_names
RUBYGEMS_RAW_EMAILS            = "email"                # list → author_emails
RUBYGEMS_RAW_LICENSE           = "license"              # str → licenses
RUBYGEMS_RAW_LICENSES          = "licenses"             # list → licenses (병합)
RUBYGEMS_RAW_HOMEPAGE          = "homepage"             # str → homepage
RUBYGEMS_RAW_MD_HOMEPAGE_URI   = "metadata.homepage_uri"    # str → homepage (fallback)
RUBYGEMS_RAW_MD_BUG_TRACKER    = "metadata.bug_tracker_uri" # str → bug_tracking
RUBYGEMS_RAW_MD_SOURCE_CODE    = "metadata.source_code_uri" # str → source_repository
RUBYGEMS_RAW_DEPS_RUNTIME      = "dependencies.runtime"     # [[name,[req,...]],...]  → runtime
RUBYGEMS_RAW_DEPS_DEVELOPMENT  = "dependencies.development" # [[name,[req,...]],...]  → development
RUBYGEMS_RAW_FILES             = "files"                # list
RUBYGEMS_REQUIREMENT_JOINER    = " AND "                # requirements 결합 구분자
# metadata (raw dict) → 제외


# ============================================================
# Placeholder 제거 규칙 (레지스트리별)
# ============================================================
# exact: 정확히 일치하면 제거
# prefix: 해당 문자열로 시작하면 제거
# src_old/cleansing/manifest_cleansing_config.py 기준으로 검증 완료

NPM_PLACEHOLDER_EXACT: List[str] = [
    'echo "Error: no test specified" && exit 1',
]
NPM_PLACEHOLDER_PREFIX: List[str] = []

PYPI_PLACEHOLDER_EXACT: List[str] = ["UNKNOWN"]
PYPI_PLACEHOLDER_PREFIX: List[str] = []

RUBYGEMS_PLACEHOLDER_EXACT: List[str] = []
RUBYGEMS_PLACEHOLDER_PREFIX: List[str] = ["TODO:"]
