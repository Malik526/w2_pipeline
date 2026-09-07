"""Route ingested documents into native text or OCR acquisition."""

from __future__ import annotations

import tempfile
from pathlib import Path

from w2_pipeline.extraction.checkbox_anchor import (
    DEFAULT_INTERIOR_INK_THRESHOLD,
    RetirementPlanDetection,
    detect_retirement_plan,
)
from w2_pipeline.extraction.checkbox_vision import detect_box_13_retirement_plan_mark
from w2_pipeline.extraction.deskew import DEFAULT_TRIGGER_THRESHOLD_DEGREES, deskew_image_if_needed
from w2_pipeline.extraction.models import (
    AcquisitionRoute,
    Box13CheckboxEvidence,
    ObservationSet,
    TextObservation,
)
from w2_pipeline.extraction.native_pdf import extract_native_pdf_observations
from w2_pipeline.extraction.ocr import TesseractOcrAdapter
from w2_pipeline.extraction.ocr_backend import OcrAdapter
from w2_pipeline.extraction.pdf_rendering import rendered_pdf_pages
from w2_pipeline.ingestion.models import IngestedDocument, PdfTextMode, SourceDocumentType
from w2_pipeline.ingestion.pdf_inspector import inspect_pdf


def _anchor_relative_evidence(
    detection: RetirementPlanDetection, *, detection_method: str, fallback_used: bool
) -> Box13CheckboxEvidence:
    """Carry every discrete Phase 8C.10 evidence field into the structured,
    per-document provenance record -- never collapsed into one score."""

    checkbox = detection.checkbox
    return Box13CheckboxEvidence(
        detection_method=detection_method,
        fallback_used=fallback_used,
        anchor_found=detection.anchor_found,
        checkbox_found=detection.checkbox_found,
        anchor_distance_px=checkbox.anchor_distance_px if checkbox is not None else None,
        horizontal_alignment_offset_px=checkbox.horizontal_alignment_offset_px if checkbox is not None else None,
        shape_score=checkbox.shape_score if checkbox is not None else None,
        interior_ink_ratio=detection.interior_ink_ratio,
        decision_margin=detection.decision_margin,
    )


class ObservationAcquirer:
    """Build common observations from an already-ingested source document.

    `ocr_adapter` accepts any backend implementing the `OcrAdapter` contract
    (Tesseract by default, or PaddleOCR); the routing and parsing logic below
    is backend-agnostic. OCR-routed acquisition also runs a backend-neutral
    pixel-based Box 13 checkbox detector (`checkbox_vision`) directly on the
    page image, independent of whichever OCR backend produced the text
    observations.

    `enable_conditional_deskew` (Phase 8C.9, default `False` -- an explicit
    opt-in, not a default-on production behavior change) runs
    `w2_pipeline.extraction.deskew` against the page image *before* OCR and
    checkbox detection, for the plain-image acquisition path only (PDF
    paths are unaffected -- this dataset's documents are all images, and
    extending deskew to PDF-rendered pages is out of this phase's scope).
    An already-upright image is passed through completely untouched (the
    original path, never a re-saved copy); only a genuinely triggered
    correction produces a new file, and both OCR and checkbox detection
    then run on that corrected file so the two systems never disagree
    about which image they saw.

    `enable_anchor_relative_checkbox` (default `True` as of Phase 8C.11;
    introduced opt-in in Phase 8C.10) replaces the fixed-page-zone
    `box_13.retirement_plan` detector with
    `w2_pipeline.extraction.checkbox_anchor.detect_retirement_plan` for
    the plain-image acquisition path, reusing the same OCR observations
    already produced (no second OCR pass). Phase 8C.10's 600-document
    benchmark showed this is strictly better than the fixed-zone
    detector it replaces (600/600 vs 540/600 checkbox classification,
    zero non-checkbox regressions), so it is now the normal production
    path -- not an experimental opt-in. If the anchor or checkbox
    cannot be localized, this falls back to the original fixed-zone
    detector rather than fabricating a result -- which detector actually
    produced the result is recorded both in `ObservationSet.warnings`
    (an explicit, measurable note, not silent) and structurally in
    `ObservationSet.box_13_checkbox_evidence.detection_method`, never
    inferred after the fact. Passing `enable_anchor_relative_checkbox=
    False` is retained only as a diagnostic/backward-comparison override
    that reproduces the old fixed-zone-only behavior; production callers
    should not pass it.
    """

    def __init__(
        self,
        ocr_adapter: OcrAdapter | None = None,
        *,
        enable_conditional_deskew: bool = False,
        deskew_threshold_degrees: float = DEFAULT_TRIGGER_THRESHOLD_DEGREES,
        deskew_output_dir: Path | None = None,
        enable_anchor_relative_checkbox: bool = True,
        checkbox_interior_ink_threshold: float = DEFAULT_INTERIOR_INK_THRESHOLD,
    ) -> None:
        self.ocr_adapter = ocr_adapter or TesseractOcrAdapter()
        self.enable_conditional_deskew = enable_conditional_deskew
        self.deskew_threshold_degrees = deskew_threshold_degrees
        self._deskew_output_dir = deskew_output_dir
        self.enable_anchor_relative_checkbox = enable_anchor_relative_checkbox
        self.checkbox_interior_ink_threshold = checkbox_interior_ink_threshold

    def warm_up(self) -> None:
        """Force the OCR backend's one-time readiness cost now, if it has one."""

        self.ocr_adapter.warm_up()

    @property
    def deskew_output_dir(self) -> Path:
        if self._deskew_output_dir is None:
            self._deskew_output_dir = Path(tempfile.mkdtemp(prefix="w2_pipeline_deskew_"))
        return self._deskew_output_dir

    def acquire(self, ingested_document: IngestedDocument) -> ObservationSet:
        """Acquire text observations using native PDF text or OCR."""

        path = Path(ingested_document.source_path)
        if ingested_document.source_type == SourceDocumentType.PDF:
            return self._acquire_pdf(path, ingested_document)

        resolved_path = self._resolve_image_path(path)
        observations = self.ocr_adapter.extract_image(resolved_path, page_number=1)
        box_13_visual_marks, warnings, evidence = self._detect_box_13_visual_marks_for_image(
            resolved_path, observations
        )
        return ObservationSet(
            observations=observations,
            route=AcquisitionRoute.OCR,
            box_13_visual_marks=box_13_visual_marks,
            warnings=warnings,
            box_13_checkbox_evidence=evidence,
        )

    def _detect_box_13_visual_marks_for_image(
        self, image_path: Path, observations: list[TextObservation]
    ) -> tuple[dict[str, bool], list[str], Box13CheckboxEvidence]:
        if not self.enable_anchor_relative_checkbox:
            marks, warnings = self._detect_box_13_visual_marks(image_paths=[image_path])
            evidence = Box13CheckboxEvidence(detection_method="fixed_zone_disabled", fallback_used=False)
            return marks, warnings, evidence

        try:
            detection = detect_retirement_plan(
                image_path, observations, interior_ink_threshold=self.checkbox_interior_ink_threshold
            )
        except Exception as exc:  # noqa: BLE001 - optional signal, never fatal
            marks, warnings = self._detect_box_13_visual_marks(image_paths=[image_path])
            evidence = Box13CheckboxEvidence(detection_method="fixed_zone_fallback", fallback_used=True)
            return (
                marks,
                [
                    *warnings,
                    f"Box 13 retirement_plan: anchor-relative detection raised {exc.__class__.__name__}; "
                    "fell back to fixed-zone detector.",
                ],
                evidence,
            )

        if detection.retirement_plan is not None:
            evidence = _anchor_relative_evidence(detection, detection_method="anchor_relative", fallback_used=False)
            return (
                {"retirement_plan": detection.retirement_plan},
                ["Box 13 retirement_plan: anchor-relative detection used."],
                evidence,
            )

        marks, warnings = self._detect_box_13_visual_marks(image_paths=[image_path])
        evidence = _anchor_relative_evidence(detection, detection_method="fixed_zone_fallback", fallback_used=True)
        return (
            marks,
            [
                *warnings,
                "Box 13 retirement_plan: anchor-relative detection could not localize the "
                "anchor/checkbox; fell back to fixed-zone detector.",
            ],
            evidence,
        )

    def _resolve_image_path(self, path: Path) -> Path:
        if not self.enable_conditional_deskew:
            return path
        resolved_path, _angle, _corrected = deskew_image_if_needed(
            path, output_dir=self.deskew_output_dir, threshold_degrees=self.deskew_threshold_degrees
        )
        return resolved_path

    def _acquire_pdf(self, path: Path, ingested_document: IngestedDocument) -> ObservationSet:
        if ingested_document.pdf_text_mode == PdfTextMode.EMBEDDED_TEXT:
            observations = extract_native_pdf_observations(path)
            return ObservationSet(observations=observations, route=AcquisitionRoute.NATIVE_PDF)

        if ingested_document.pdf_text_mode == PdfTextMode.IMAGE_ONLY:
            observations = self.ocr_adapter.extract_pdf_pages(path)
            box_13_visual_marks, warnings = self._detect_box_13_visual_marks(pdf_path=path)
            return ObservationSet(
                observations=observations,
                route=AcquisitionRoute.OCR,
                box_13_visual_marks=box_13_visual_marks,
                warnings=warnings,
            )

        if ingested_document.pdf_text_mode == PdfTextMode.MIXED:
            inspection = inspect_pdf(path)
            native_pages = {
                page.page_number for page in inspection.pages if page.has_usable_embedded_text
            }
            ocr_pages = {
                page.page_number for page in inspection.pages if not page.has_usable_embedded_text
            }
            observations = [
                *extract_native_pdf_observations(path, page_numbers=native_pages),
                *self.ocr_adapter.extract_pdf_pages(path, page_numbers=ocr_pages),
            ]
            box_13_visual_marks, warnings = self._detect_box_13_visual_marks(
                pdf_path=path, pdf_page_numbers=ocr_pages
            )
            return ObservationSet(
                observations=sorted(
                    observations,
                    key=lambda observation: (
                        observation.page,
                        observation.bbox.y0,
                        observation.bbox.x0,
                    ),
                ),
                route=AcquisitionRoute.MIXED,
                box_13_visual_marks=box_13_visual_marks,
                warnings=warnings,
            )

        observations = self.ocr_adapter.extract_pdf_pages(path)
        box_13_visual_marks, warnings = self._detect_box_13_visual_marks(pdf_path=path)
        return ObservationSet(
            observations=observations,
            route=AcquisitionRoute.OCR,
            box_13_visual_marks=box_13_visual_marks,
            warnings=warnings,
        )

    def _detect_box_13_visual_marks(
        self,
        *,
        image_paths: list[Path] | None = None,
        pdf_path: Path | None = None,
        pdf_page_numbers: set[int] | None = None,
    ) -> tuple[dict[str, bool], list[str]]:
        """Run the visual checkbox detector on every OCR-routed page image.

        Results are OR'd across pages: a single-page W-2 is the only
        supported document shape, so this is a defensive merge rather than a
        meaningful multi-page aggregation. Detector failures degrade to "no
        mark detected" rather than failing extraction, since this signal is
        always an additive OR alongside the existing OCR-text-based fallback.
        """

        if pdf_path is not None:
            with rendered_pdf_pages(pdf_path, page_numbers=pdf_page_numbers) as pages:
                candidate_paths = [image_path for _, image_path in pages]
                return self._scan_pages_for_box_13_marks(candidate_paths)
        return self._scan_pages_for_box_13_marks(image_paths or [])

    def _scan_pages_for_box_13_marks(
        self, image_paths: list[Path]
    ) -> tuple[dict[str, bool], list[str]]:
        retirement_plan_detected = False
        warnings: list[str] = []
        for image_path in image_paths:
            try:
                if detect_box_13_retirement_plan_mark(image_path):
                    retirement_plan_detected = True
            except Exception as exc:  # noqa: BLE001 - optional signal, never fatal
                warnings.append(f"Box 13 visual checkbox detection failed: {exc}")
        if not image_paths:
            return {}, warnings
        return {"retirement_plan": retirement_plan_detected}, warnings
