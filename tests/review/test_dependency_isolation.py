"""Structural safeguards: review/downstream code has no benchmark-ground-
truth dependency and no extraction-pipeline coupling.

Same AST-based technique as `tests/validation/test_isolation.py` and
`tests/extraction/pipeline_b/test_extractor.py`.
"""

from __future__ import annotations

import ast
from pathlib import Path

import w2_pipeline.downstream as downstream_package
import w2_pipeline.review as review_package

_FORBIDDEN_MODULE_PREFIXES = ("w2_pipeline.evaluation", "w2_pipeline.extraction")


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


def _package_source_files(package: object) -> list[Path]:
    package_dir = Path(package.__file__).parent
    return sorted(package_dir.glob("*.py"))


def test_review_package_has_no_evaluation_or_extraction_dependency() -> None:
    for source_path in _package_source_files(review_package):
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


def test_downstream_package_has_no_evaluation_or_extraction_dependency() -> None:
    for source_path in _package_source_files(downstream_package):
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


def test_review_and_downstream_packages_were_actually_checked() -> None:
    assert len(_package_source_files(review_package)) >= 5
    assert len(_package_source_files(downstream_package)) >= 4
