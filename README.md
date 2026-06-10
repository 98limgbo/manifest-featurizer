# manifest-featurizer

A data preparation pipeline that extracts metadata from package manifests (npm, PyPI, RubyGems) and generates features for malicious package detection.

> **Scope**: This project covers data preparation only. Model training and inference are out of scope.

---

## Installation

Requires Python 3.10+. Dependencies are managed with [uv](https://github.com/astral-sh/uv).

```bash
uv venv
uv pip install -e .
```

---

## Quick Start

**Using the provided sample data:**

```bash
# Run the pipeline on the included sample data
python -m src.pipeline
```

Sample manifests are provided under `data/sample/` (one package per registry and label). Copy them into `data/00_manifest/` to try the pipeline without preparing your own dataset:

```bash
# Windows
xcopy /E /I data\sample data\00_manifest

# macOS / Linux
cp -r data/sample/. data/00_manifest/
```

This produces `data/05_preprocessed/preprocessed.csv` — the final feature matrix ready for model training.

---

## Pipeline

```
00_manifest → [parse] → 01_parsed → [cleanse] → 02_cleansed
→ [normalize] → 03_normalized → [merge + featurize] → 04_features
→ [preprocess] → 05_preprocessed
```

| Step | Output | Description |
|---|---|---|
| Parse | `01_parsed/` | Raw fields extracted from manifests |
| Cleanse | `02_cleansed/` | Placeholders removed, duplicates deduplicated |
| Normalize | `03_normalized/` | Field names unified across registries |
| Featurize | `04_features/features.csv` | Binary, count, length, version, license, dependency features |
| Preprocess | `05_preprocessed/preprocessed.csv` | log1p applied to skewed numeric features |

---

## Data Structure

Place manifest files under:

```
data/00_manifest/{source}/{registry}/{label}/{name}##{version}/
```

- `source`: `old` (collected before 2025) / `new` (collected after 2025)
- `registry`: `npm` / `pypi` / `rubygems`
- `label`: `malicious` / `benign` / `spam` / `disputed`

**Package ID format** (auto-generated from folder path):
```
source::registry::label::name::version
```

Sample data is provided under `data/sample/` with the same structure.

---

## Scripts

### Ingest packages from an external archive directory

Extracts manifests from compressed archives (`.tgz` for npm) and places them into `data/00_manifest/`.

```bash
python -m scripts.ingest_packages <source_dir> <registry> <label> [--source new]

# Example: ingest npm spam packages
python -m scripts.ingest_packages "D:/npm_spam" npm spam
```

Supports npm out of the box. Add other registries in `scripts/ingest_packages.py::_REGISTRY_CONFIG`.

### Validate pipeline outputs

Structural checks on all pipeline stages (row counts, column schema, value ranges, malicious vs. benign distribution).

```bash
python -m scripts.validate
```

### Spot-check semantic correctness

Verifies that placeholder cleansing and license featurization behave as expected on a sample of packages.

```bash
python -m scripts.spot_check [--n N]
```

---

## Extending the Pipeline

**Add a new registry** (e.g., Maven):
1. Create `data/00_manifest/{source}/maven/{label}/`
2. Write `src/parsing/maven.py`
3. Add field mappings to `config/registry_schema.py`
4. Add one entry to `src/loader.py::_REGISTRY_CONFIG`

**Add a new label**: Create the folder — no code changes needed.

**Change preprocessing rules**: Edit `config/preprocess_schema.py::LOG_TRANSFORM_FEATURES`.

---

For architecture details, module roles, and function signatures, see [`CLAUDE.md`](CLAUDE.md).  
This file serves as developer documentation and is useful for anyone — not just Claude Code users. It is also automatically loaded by [Claude Code](https://claude.ai/code) when working in this repository.

---

## License

MIT License. See [`LICENSE`](LICENSE).
