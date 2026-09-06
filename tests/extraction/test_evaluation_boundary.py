"""Phase 8A: extraction runtime must not depend on benchmark ground truth.

`w2_pipeline.evaluation.inputs.ExtractionInput` is the one deliberate
exception: it is the annotation-free input contract extractors receive
(document path, document ID, optional tax-year hint, source label --
`extra="forbid"`, no ground truth or dataset annotations anywhere in it),
not a ground-truth-bearing type. Every other `w2_pipeline.evaluation`
submodule (`comparison`, `manifest`, `runner`, `external_symage`,
`predictions`, `dataset`, `synthetic`, `reporting`, ...) carries or
derives from ground truth and must never be imported by extraction
runtime code. Same AST-based technique as
`tests/validation/test_isolation.py` and
`tests/review/test_dependency_isolation.py`.
"""

from __future__ import annotations

import ast
from pathlib import Path

import w2_pipeline.extraction as extraction_package

_ALLOWED_EVALUATION_SUBMODULES = frozenset({"w2_pipeline.evaluation.inputs"})


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


def _extraction_source_files() -> list[Path]:
    package_dir = Path(extraction_package.__file__).parent
    return sorted(package_dir.rglob("*.py"))


def test_extraction_only_imports_the_annotation_free_input_contract() -> None:
    for source_path in _extraction_source_files():
        imported = _imported_modules(source_path)
        evaluation_imports = {
            module
            for module in imported
            if module == "w2_pipeline.evaluation" or module.startswith("w2_pipeline.evaluation.")
        }
        disallowed = evaluation_imports - _ALLOWED_EVALUATION_SUBMODULES
        assert not disallowed, (
            f"{source_path.relative_to(Path(extraction_package.__file__).parent)} "
            f"imports ground-truth-bearing evaluation module(s): {disallowed}"
        )


def test_extraction_source_files_were_actually_checked() -> None:
    assert len(_extraction_source_files()) >= 10
