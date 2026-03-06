# Kindling - CLAUDE.md

## Project Overview

Kindling is a lightweight, profile-driven FHIR R4 synthetic data generator built on `fhir.resources`. It generates realistic, deterministic healthcare data (FHIR R4 bundles) from YAML/JSON profiles and pre-configured personas.

**Version:** 0.1.0 (Alpha)
**License:** Apache 2.0
**Python:** 3.9 - 3.12

## Quick Start

```bash
# Install dependencies (creates venv automatically)
uv sync --dev

# Run tests
uv run pytest

# Run the CLI
uv run kindling --help
uv run kindling --persona mary_diabetes --output mary.json
uv run kindling-validate mary.json
```

## Project Structure

```
kindling/
├── kindling/
│   ├── generator.py          # Core Generator class - orchestrates all generation
│   ├── resource_factory.py   # Creates FHIR resources from definition dicts
│   ├── bundle_assembler.py   # Assembles resources into FHIR Bundles
│   ├── validator.py          # FHIR validation (structure, references, resource-specific)
│   ├── cli.py                # Main CLI entry point (click-based)
│   ├── validate_cli.py       # Validation CLI endpoint
│   ├── profile_parser.py     # Parses YAML/JSON profile definitions
│   ├── persona_loader.py     # Loads built-in persona YAML files
│   ├── config.py             # Constants: system URLs, defaults, medical codes
│   ├── fhir_compat.py        # Monkey-patches for fhir.resources v7.x R4 compat
│   ├── personas/             # Built-in persona YAML files
│   └── utils/
│       ├── random_utils.py   # SeededRandom for deterministic generation
│       └── r4_converter.py   # R5→R4 field conversion
├── tests/                    # pytest test suite (~9 test modules)
├── examples/                 # Usage examples and sample profiles
└── pyproject.toml            # All project and tool configuration
```

## Architecture

- **Generator** is the main entry point. It takes a profile or persona and produces FHIR bundles.
- **ResourceFactory** creates individual FHIR resources (Patient, Condition, Observation, etc.) from dictionary definitions.
- **BundleAssembler** collects resources into transaction or collection bundles with proper references.
- **SeededRandom** ensures deterministic output for a given seed.
- **fhir_compat.py** patches `fhir.resources` v7.x (which targets R5) to work with R4 output.

## Code Style & Tooling

All configuration lives in `pyproject.toml`:

- **Formatter:** black (line-length: 100)
- **Linter:** ruff (rules: E, F, I, N, W; line-length: 100)
- **Type checker:** mypy (python 3.9, ignore_missing_imports=true)
- **Tests:** pytest with pytest-cov

Run before committing:
```bash
uv run black kindling tests
uv run ruff check kindling tests
uv run mypy kindling
uv run pytest
```

## Key Patterns

- Profile definitions are YAML dicts with `demographics`, `resources`, and optional `rules` sections.
- Rules use `when`/`then` conditions for conditional resource generation (e.g., "when condition is diabetes, then add HbA1c observations").
- Bundle methods: `POST` (server assigns IDs), `PUT` (client IDs), `CONDITIONAL` (identity-based upserts).
- URN UUIDs are used in transaction bundles for internal references, mapped to real references on assembly.

## Dependencies

**Runtime:** fhir.resources (>=7.1.0), pyyaml, click, pydantic (>=2.0), httpx, faker, python-dateutil
**Dev:** pytest, pytest-cov, pytest-asyncio, black, ruff, mypy

## Known Issues & Technical Debt

1. **fhir.resources v7.x compatibility** - The library moved from R4 to R5 in v7.x. `fhir_compat.py` uses monkey-patches to maintain R4 output. These patches are fragile and may break on library updates.
2. **`--server` upload not implemented** - CLI accepts the flag but raises "not yet implemented".
3. **Unused dependencies** - `faker` and `httpx` are declared but not currently used in the codebase.
4. **Silent reference failures** - `BundleAssembler._update_references()` silently ignores update failures instead of warning.
5. **Large methods** - `generator.py:_apply_rule()` (~150 lines), `cli.py:main()` (~141 lines), and `resource_factory.py:create_encounter()` (~143 lines) could be broken up.
6. **Loose input validation** - Many methods accept `Dict[str, Any]` without validating structure; bad input can produce confusing errors.
