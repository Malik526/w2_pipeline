"""Structural safeguards against Phase 6 depending on things it must not.

Validation must judge an already-extracted `W2Document` using only the
canonical contract and its own rules -- never benchmark ground truth
(`w2_pipeline.evaluation`, which is annotation-bearing) and never a
specific extraction pipeline's internals (`w2_pipeline.extraction`, which
would make validation backend-specific). These are enforced with AST-based
import inspection, the same technique
`tests/extraction/pipeline_b/test_extractor.py` uses to keep Pipeline B
isolated from Pipeline A.
"""

from __future__ import annotations

import ast
from pathlib import Path

import w2_pipeline.validation as validation_package

_FORBIDDEN_MODULE_PREFIXES = (
    "w2_pipeline.evaluation",
    "w2_pipeline.extraction",
    "w2_pipeline.ingestion",
)


def _imported_modules(source_path: Path) -> set[str]:
    with source_path.open(encoding="utf-8") as file_obj:
        tree = ast.parse(file_obj.read())

    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _validation_source_files() -> list[Path]:
    package_dir = Path(validation_package.__file__).parent
    return sorted(package_dir.glob("*.py"))


def test_no_validation_module_imports_evaluation_or_extraction_packages() -> None:
    for source_path in _validation_source_files():
        imported = _imported_modules(source_path)
        forbidden_hits = {
            module
            for module in imported
            if any(
                module == prefix or module.startswith(f"{prefix}.")
                for prefix in _FORBIDDEN_MODULE_PREFIXES
            )
        }
        assert not forbidden_hits, f"{source_path.name} imports forbidden module(s): {forbidden_hits}"


def test_validation_source_files_were_actually_checked() -> None:
    # A guard against this test silently checking zero files if the
    # package layout ever changes.
    assert len(_validation_source_files()) >= 5
