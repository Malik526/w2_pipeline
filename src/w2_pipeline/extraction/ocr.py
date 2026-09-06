"""Tesseract OCR adapter for Pipeline A."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import re
import shutil
import subprocess
from pathlib import Path

from w2_pipeline.extraction.errors import MissingOcrDependencyError, OcrExecutionError
from w2_pipeline.extraction.models import BoundingBox, ObservationSource, TextObservation
from w2_pipeline.extraction.pdf_rendering import rendered_pdf_pages

_TOP_IDENTIFIER_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_SUPPLEMENTAL_EIN_RE = re.compile(r"\b\d{2}-\d{7}\b")
SUPPORTED_MAIN_PAGE_SEGMENTATION_MODES = (3, 11, 12)
SUPPORTED_SUPPLEMENTAL_PAGE_SEGMENTATION_MODES = (6, 11)


@dataclass(frozen=True)
class SupplementalTargetZone:
    """One geo-fenced region a targeted supplemental OCR pass may recover text for.

    ``zone`` ratios are ``(x0, x1, y0, y1)`` relative to the reference OCR
    pass's own observation extent, matching the ratio convention the parser's
    OCR fallback zones already use for the same physical page regions
    (``parser_2026.py``: employee name/EIN/federal-box fallback zones). An
    optional ``pattern`` requires the recovered text to also look like the
    target content (e.g. an EIN shape), for target fields with a reliable
    strict shape; free-text fields such as a name have no such pattern.
    """

    zone: tuple[float, float, float, float]
    pattern: re.Pattern[str] | None = None


# PSM 6 stays the existing, single-purpose SSN-recovery pass (top identifier
# region). PSM 11's zones are restricted to fields whose parser fallback
# uses first-match zone logic (`_first_regex_text_in_zone`/
# `_first_money_text_in_zone`), not the join-all `_zone_text` logic used for
# the employee-name zone. The name zone was dropped after a 5-document smoke
# test showed a disqualifying regression there: `_zone_text` joins every
# observation in its zone rather than picking one, so PSM 11's supplemental
# pass and PSM 3's main pass both landing readings of the same name in that
# zone corrupted `employee.first_name` via text duplication (see
# docs/experiments/pipeline-a-extraction-history.md, "Targeted Supplemental
# PSM 11 Smoke Test"). `employer.ein` and federal Boxes 3/5/6 were
# unaffected by that failure mode and remain PSM 11's approved target set;
# they intentionally still exclude Box 13 (owned by checkbox_vision.py) and
# SSN (owned by PSM 6). Each zone tuple mirrors the matching fallback zone
# in parser_2026.py so a recovered supplemental observation lands in the
# same region the parser's own fallback will later search.
_SUPPLEMENTAL_TARGET_ZONES: dict[int, tuple[SupplementalTargetZone, ...]] = {
    6: (SupplementalTargetZone(zone=(0.25, 0.55, 0.10, 0.17), pattern=_TOP_IDENTIFIER_RE),),
    11: (
        # employer.ein
        SupplementalTargetZone(zone=(0.20, 0.42, 0.16, 0.24), pattern=_SUPPLEMENTAL_EIN_RE),
        # federal_wages_and_taxes.box_3_social_security_wages
        SupplementalTargetZone(zone=(0.55, 0.80, 0.245, 0.290)),
        # federal_wages_and_taxes.box_5_medicare_wages_and_tips
        SupplementalTargetZone(zone=(0.55, 0.80, 0.300, 0.345)),
        # federal_wages_and_taxes.box_6_medicare_tax_withheld
        SupplementalTargetZone(zone=(0.80, 1.00, 0.300, 0.350)),
    ),
}


@dataclass(frozen=True)
class TesseractOcrConfig:
    """Configuration for Pipeline A's Tesseract OCR component."""

    page_segmentation_mode: int = 3
    supplemental_page_segmentation_modes: tuple[int, ...] = (6,)

    def __post_init__(self) -> None:
        if self.page_segmentation_mode not in SUPPORTED_MAIN_PAGE_SEGMENTATION_MODES:
            supported = ", ".join(str(mode) for mode in SUPPORTED_MAIN_PAGE_SEGMENTATION_MODES)
            raise ValueError(
                "Unsupported main Tesseract page segmentation mode "
                f"{self.page_segmentation_mode}; expected one of: {supported}."
            )
        object.__setattr__(
            self,
            "supplemental_page_segmentation_modes",
            tuple(self.supplemental_page_segmentation_modes),
        )
        for mode in self.supplemental_page_segmentation_modes:
            if mode not in SUPPORTED_SUPPLEMENTAL_PAGE_SEGMENTATION_MODES:
                supported = ", ".join(
                    str(mode) for mode in SUPPORTED_SUPPLEMENTAL_PAGE_SEGMENTATION_MODES
                )
                raise ValueError(
                    f"Unsupported supplemental Tesseract page segmentation mode {mode}; "
                    f"expected one of: {supported}."
                )


class TesseractOcrAdapter:
    """Run local Tesseract OCR and convert TSV output to observations."""

    def __init__(
        self,
        executable: str = "tesseract",
        *,
        config: TesseractOcrConfig | None = None,
        page_segmentation_mode: int | None = None,
        supplemental_page_segmentation_modes: tuple[int, ...] | None = None,
    ) -> None:
        if config is not None and (
            page_segmentation_mode is not None
            or supplemental_page_segmentation_modes is not None
        ):
            raise ValueError(
                "Pass either TesseractOcrConfig or explicit OCR settings, not both."
            )
        self.config = config or TesseractOcrConfig(
            page_segmentation_mode=(
                page_segmentation_mode
                if page_segmentation_mode is not None
                else TesseractOcrConfig.page_segmentation_mode
            ),
            supplemental_page_segmentation_modes=(
                supplemental_page_segmentation_modes
                if supplemental_page_segmentation_modes is not None
                else TesseractOcrConfig.supplemental_page_segmentation_modes
            ),
        )
        self.executable = executable
        self.page_segmentation_mode = self.config.page_segmentation_mode
        self.supplemental_page_segmentation_modes = (
            self.config.supplemental_page_segmentation_modes
        )

    def ensure_available(self) -> None:
        """Raise an actionable error when the OCR binary is missing."""

        if shutil.which(self.executable) is None:
            raise MissingOcrDependencyError(
                "Tesseract OCR runtime is not installed or is not on PATH. "
                "Install the `tesseract` system package to enable Pipeline A OCR."
            )

    def extract_image(self, image_path: str | Path, *, page_number: int = 1) -> list[TextObservation]:
        """OCR one image file into text observations."""

        self.ensure_available()
        path = Path(image_path)
        observations = parse_tesseract_tsv(
            self._run_tesseract(path, page_segmentation_mode=self.page_segmentation_mode),
            page_number=page_number,
        )
        for supplemental_mode in self.supplemental_page_segmentation_modes:
            supplemental_observations = parse_tesseract_tsv(
                self._run_tesseract(path, page_segmentation_mode=supplemental_mode),
                page_number=page_number,
                is_supplemental=True,
            )
            observations.extend(
                _targeted_supplemental_observations(
                    supplemental_observations,
                    target_zones=_SUPPLEMENTAL_TARGET_ZONES[supplemental_mode],
                    reference_observations=[*observations, *supplemental_observations],
                )
            )
        return observations

    def extract_pdf_pages(
        self,
        pdf_path: str | Path,
        *,
        page_numbers: set[int] | None = None,
    ) -> list[TextObservation]:
        """Render selected PDF pages and OCR them into observations."""

        self.ensure_available()
        observations: list[TextObservation] = []
        with rendered_pdf_pages(pdf_path, page_numbers=page_numbers) as pages:
            for page_index, image_path in pages:
                observations.extend(self.extract_image(image_path, page_number=page_index))
        return observations

    def _run_tesseract(self, image_path: Path, *, page_segmentation_mode: int) -> str:
        command = [
            self.executable,
            str(image_path),
            "stdout",
            "--psm",
            str(page_segmentation_mode),
            "tsv",
        ]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            raise OcrExecutionError(f"Could not execute Tesseract OCR: {exc}") from exc
        if completed.returncode != 0:
            raise OcrExecutionError("Tesseract OCR failed for the source document.")
        return completed.stdout


def parse_tesseract_tsv(
    tsv_payload: str,
    *,
    page_number: int,
    is_supplemental: bool = False,
) -> list[TextObservation]:
    """Convert Tesseract TSV rows into OCR text observations."""

    observations: list[TextObservation] = []
    reader = csv.DictReader(tsv_payload.splitlines(), delimiter="\t")
    for row in reader:
        text = (row.get("text") or "").strip()
        if not text:
            continue
        confidence = _parse_confidence(row.get("conf"))
        if confidence is not None and confidence < 0:
            continue
        left = _parse_float(row.get("left"))
        top = _parse_float(row.get("top"))
        width = _parse_float(row.get("width"))
        height = _parse_float(row.get("height"))
        # Tesseract's TSV `conf` is native 0..100 (confirmed against real TSV
        # output, not assumed); rescaled to 0..1 here so it shares
        # `TextObservation.ocr_confidence`'s scale with PaddleOCR's already
        # native 0..1 `rec_scores` -- a linear rescale of the engine's own
        # real value, never a fabricated one.
        ocr_confidence = confidence / 100.0 if confidence is not None else None
        observations.append(
            TextObservation(
                text=text,
                page=page_number,
                bbox=BoundingBox(x0=left, y0=top, x1=left + width, y1=top + height),
                source=ObservationSource.OCR,
                ocr_confidence=ocr_confidence,
                is_supplemental=is_supplemental,
            )
        )
    return observations


def _targeted_supplemental_observations(
    observations: list[TextObservation],
    *,
    target_zones: tuple[SupplementalTargetZone, ...],
    reference_observations: list[TextObservation],
) -> list[TextObservation]:
    """Keep supplemental-pass output only inside its approved target zone(s).

    A targeted supplemental pass (e.g. PSM 6's SSN recovery, or PSM 11's
    name/EIN/box-3/5/6 recovery) must never behave like a second full-page
    OCR pass: without this filter its output would duplicate or corrupt
    already-successful primary-path text everywhere on the page, not just in
    the region it was added to help. Each mode's approved zones (see
    `_SUPPLEMENTAL_TARGET_ZONES`) keep it confined to exactly the fields it
    is meant to recover.
    """

    if not reference_observations:
        return []
    max_x = max(observation.bbox.x1 for observation in reference_observations)
    max_y = max(observation.bbox.y1 for observation in reference_observations)
    kept: list[TextObservation] = []
    for observation in observations:
        center_x = (observation.bbox.x0 + observation.bbox.x1) / 2
        center_y = (observation.bbox.y0 + observation.bbox.y1) / 2
        for target in target_zones:
            x0_ratio, x1_ratio, y0_ratio, y1_ratio = target.zone
            if not (x0_ratio * max_x <= center_x <= x1_ratio * max_x):
                continue
            if not (y0_ratio * max_y <= center_y <= y1_ratio * max_y):
                continue
            if target.pattern is not None and not target.pattern.search(observation.text):
                continue
            kept.append(observation)
            break
    return kept


def _parse_float(value: str | None) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _parse_confidence(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
