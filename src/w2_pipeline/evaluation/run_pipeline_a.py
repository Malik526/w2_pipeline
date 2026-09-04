"""Run Pipeline A against a Phase 3 evaluation manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from w2_pipeline.evaluation.manifest import DatasetManifestEntry, load_manifest_jsonl
from w2_pipeline.evaluation.reporting import (
    summarize_document_evaluations,
    write_markdown_report_for_json,
)
from w2_pipeline.evaluation.runner import evaluate_manifest
from w2_pipeline.extraction.acquisition import ObservationAcquirer
from w2_pipeline.extraction.ocr import (
    SUPPORTED_MAIN_PAGE_SEGMENTATION_MODES,
    TesseractOcrAdapter,
    TesseractOcrConfig,
)
from w2_pipeline.extraction.ocr_backend import OcrAdapter
from w2_pipeline.extraction.ocr_paddle import PaddleOcrAdapter, PaddleOcrConfig
from w2_pipeline.extraction.pipeline_a import PipelineAExtractor

SUPPORTED_OCR_BACKENDS = ("tesseract", "paddleocr")


def main(argv: list[str] | None = None) -> None:
    """Evaluate Pipeline A against a manifest and print aggregate metrics."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    manifest = load_manifest_jsonl(args.manifest)
    entries = _filter_entries(manifest.entries, variant_id=args.variant_id, limit=args.limit)
    extractor = _pipeline_a_extractor(
        ocr_backend=args.ocr_backend,
        tesseract_psm=args.tesseract_psm,
        paddle_device=args.paddle_device,
    )
    result = evaluate_manifest(
        entries=entries,
        manifest_base_dir=args.manifest.parent,
        extractor=extractor,
        pipeline_id="pipeline_a",
    )
    summary = summarize_document_evaluations(
        result.document_evaluations,
        pipeline_id="pipeline_a",
        entries=entries,
        benchmark_metadata=_pipeline_a_metadata(extractor, variant_id=args.variant_id),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        if not args.no_markdown_report:
            write_markdown_report_for_json(args.output_json)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Path to manifest.jsonl.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum entries to evaluate.")
    parser.add_argument(
        "--variant-id",
        default=None,
        help="Optional variant ID filter, such as external_clean_render or clean_pdf.",
    )
    parser.add_argument(
        "--tesseract-psm",
        type=int,
        choices=SUPPORTED_MAIN_PAGE_SEGMENTATION_MODES,
        default=3,
        help=(
            "Main full-page Tesseract page segmentation mode, used only when "
            "--ocr-backend tesseract is selected. Supplemental targeted PSM 6 "
            "SSN recovery remains enabled."
        ),
    )
    parser.add_argument(
        "--ocr-backend",
        choices=SUPPORTED_OCR_BACKENDS,
        default="tesseract",
        help=(
            "OCR backend behind Pipeline A's common observation boundary. "
            "PaddleOCR is the Phase 4E alternate backend under evaluation "
            "against the Tesseract incumbent."
        ),
    )
    parser.add_argument(
        "--paddle-device",
        default="cpu",
        help=(
            "PaddlePaddle execution device, used only when --ocr-backend "
            "paddleocr is selected. Examples: cpu, gpu, gpu:0. GPU execution "
            "requires a GPU-enabled paddlepaddle-gpu runtime; see "
            "docs/contracts/extraction-pipeline-a.md. Default remains cpu."
        ),
    )
    parser.add_argument("--output-json", type=Path, default=None, help="Optional summary JSON path.")
    parser.add_argument(
        "--no-markdown-report",
        action="store_true",
        help="Do not write the matching .md report when --output-json is used.",
    )
    return parser


def _pipeline_a_extractor(
    *,
    ocr_backend: str = "tesseract",
    tesseract_psm: int = 3,
    paddle_device: str = "cpu",
) -> PipelineAExtractor:
    return PipelineAExtractor(
        observation_acquirer=ObservationAcquirer(
            ocr_adapter=_build_ocr_adapter(ocr_backend, tesseract_psm, paddle_device)
        )
    )


def _build_ocr_adapter(ocr_backend: str, tesseract_psm: int, paddle_device: str = "cpu") -> OcrAdapter:
    if ocr_backend == "paddleocr":
        return PaddleOcrAdapter(config=PaddleOcrConfig(device=paddle_device))
    if ocr_backend == "tesseract":
        return TesseractOcrAdapter(config=TesseractOcrConfig(page_segmentation_mode=tesseract_psm))
    raise ValueError(f"Unsupported OCR backend {ocr_backend!r}; expected one of: {SUPPORTED_OCR_BACKENDS}.")


def _filter_entries(
    entries: list[DatasetManifestEntry],
    *,
    variant_id: str | None,
    limit: int | None,
) -> list[DatasetManifestEntry]:
    filtered = [entry for entry in entries if variant_id is None or entry.variant_id == variant_id]
    if limit is not None:
        return filtered[:limit]
    return filtered


def _pipeline_a_metadata(extractor: PipelineAExtractor, *, variant_id: str | None) -> dict:
    ocr_adapter = extractor.observation_acquirer.ocr_adapter
    return {
        "git_commit": _git_commit(),
        "ocr_backend": _ocr_backend_name(ocr_adapter),
        "ocr_configuration": _ocr_configuration_metadata(ocr_adapter),
        "variant_filter": variant_id,
    }


def _ocr_backend_name(ocr_adapter: OcrAdapter) -> str:
    if isinstance(ocr_adapter, PaddleOcrAdapter):
        return "paddleocr"
    return "tesseract"


def _ocr_configuration_metadata(ocr_adapter: OcrAdapter) -> dict:
    if isinstance(ocr_adapter, PaddleOcrAdapter):
        config = ocr_adapter.config
        return {
            "lang": config.lang,
            "device": config.device,
            "use_doc_orientation_classify": config.use_doc_orientation_classify,
            "use_doc_unwarping": config.use_doc_unwarping,
            "use_textline_orientation": config.use_textline_orientation,
        }
    return {
        "main_page_segmentation_mode": ocr_adapter.page_segmentation_mode,
        "page_segmentation_mode": ocr_adapter.page_segmentation_mode,
        "supplemental_page_segmentation_modes": list(
            ocr_adapter.supplemental_page_segmentation_modes
        ),
    }


def _git_commit() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


if __name__ == "__main__":
    main()
