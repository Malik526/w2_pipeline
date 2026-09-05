from decimal import Decimal
from pathlib import Path

import pytest
from PIL import Image

from w2_pipeline.evaluation.inputs import ExtractionInput
from w2_pipeline.evaluation.manifest import DatasetSource
from w2_pipeline.extraction.pipeline_b.config import PipelineBConfig
from w2_pipeline.extraction.pipeline_b.errors import (
    MalformedModelOutputError,
    SchemaValidationError,
)
from w2_pipeline.extraction.pipeline_b.extractor import PipelineBExtractor
from w2_pipeline.extraction.pipeline_b.models import PipelineBExtractionResult
from w2_pipeline.ingestion import ingest_document

_VALID_RESPONSE = (
    '{"employee": {"first_name": "Ada", "last_name": "Lovelace"}, '
    '"employer": {"name": "Acme"}, '
    '"federal_wages_and_taxes": {"box_1_wages_tips_other_compensation": "1234.56"}, '
    '"box_12_entries": [], "box_13": {"retirement_plan": true}, '
    '"box_14_entries": [], "tipped_occupation_codes": [], "state_local_entries": []}'
)


class _FakeRuntime:
    def __init__(self, response: str) -> None:
        self.config = PipelineBConfig()
        self.load_duration_seconds = 12.5
        self.gpu_diagnostics = {"cuda_available": True}
        self._response = response
        self.calls: list[tuple[object, str]] = []

    def generate(self, image_path: object, prompt_text: str) -> str:
        self.calls.append((image_path, prompt_text))
        return self._response


def _sample_png(tmp_path: Path) -> Path:
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (20, 10), color="white").save(image_path)
    return image_path


def test_extract_ingested_returns_valid_canonical_result(tmp_path: Path) -> None:
    image_path = _sample_png(tmp_path)
    ingested = ingest_document(image_path, document_id="doc-1")
    runtime = _FakeRuntime(_VALID_RESPONSE)

    result = PipelineBExtractor(runtime=runtime).extract_ingested(ingested)

    assert isinstance(result, PipelineBExtractionResult)
    assert result.pipeline == "pipeline_b"
    assert result.route == "vlm"
    assert result.document.employee.first_name == "Ada"
    assert result.document.federal_wages_and_taxes.box_1_wages_tips_other_compensation == Decimal(
        "1234.56"
    )
    assert result.model_load_duration_seconds == 12.5
    assert result.raw_response_length == len(_VALID_RESPONSE)
    assert result.duration_seconds >= 0
    assert len(runtime.calls) == 1


def test_extract_ingested_raises_for_malformed_json(tmp_path: Path) -> None:
    image_path = _sample_png(tmp_path)
    ingested = ingest_document(image_path, document_id="doc-2")
    runtime = _FakeRuntime("not json at all")

    with pytest.raises(MalformedModelOutputError):
        PipelineBExtractor(runtime=runtime).extract_ingested(ingested)


def test_extract_ingested_raises_for_schema_validation_failure(tmp_path: Path) -> None:
    image_path = _sample_png(tmp_path)
    ingested = ingest_document(image_path, document_id="doc-3")
    runtime = _FakeRuntime('{"box_12_entries": [{"code": "TOOLONG", "amount": "1.00"}]}')

    with pytest.raises(SchemaValidationError):
        PipelineBExtractor(runtime=runtime).extract_ingested(ingested)


def test_extract_via_extraction_input_matches_evaluator_boundary(tmp_path: Path) -> None:
    image_path = _sample_png(tmp_path)
    runtime = _FakeRuntime(_VALID_RESPONSE)

    extraction_input = ExtractionInput(
        document_path=image_path,
        document_id="doc-4",
        source=DatasetSource.HUGGINGFACE,
        tax_year_hint=2026,
    )

    result = PipelineBExtractor(runtime=runtime).extract(extraction_input)

    assert result.document.metadata.document_id == "doc-4"
    assert not hasattr(extraction_input, "tokens")
    assert not hasattr(extraction_input, "funsd_json")


def test_extractor_prompt_never_receives_ground_truth(tmp_path: Path) -> None:
    image_path = _sample_png(tmp_path)
    ingested = ingest_document(image_path, document_id="doc-5")
    runtime = _FakeRuntime(_VALID_RESPONSE)

    PipelineBExtractor(runtime=runtime).extract_ingested(ingested)

    _, prompt_text = runtime.calls[0]
    assert "Ada" not in prompt_text
    assert "Lovelace" not in prompt_text


def test_pipeline_b_extractor_module_has_no_pipeline_a_dependency() -> None:
    import ast

    import w2_pipeline.extraction.pipeline_b.extractor as extractor_module

    with open(extractor_module.__file__, encoding="utf-8") as file_obj:
        tree = ast.parse(file_obj.read())

    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden_modules = {
        "w2_pipeline.extraction.ocr",
        "w2_pipeline.extraction.ocr_paddle",
        "w2_pipeline.extraction.ocr_backend",
        "w2_pipeline.extraction.parser_2026",
        "w2_pipeline.extraction.acquisition",
    }
    assert imported_modules.isdisjoint(forbidden_modules)
