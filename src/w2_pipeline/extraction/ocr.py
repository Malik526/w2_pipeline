"""Tesseract OCR adapter for Pipeline A."""

from __future__ import annotations

import csv
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf

from w2_pipeline.extraction.errors import MissingOcrDependencyError, OcrExecutionError
from w2_pipeline.extraction.models import BoundingBox, ObservationSource, TextObservation


class TesseractOcrAdapter:
    """Run local Tesseract OCR and convert TSV output to observations."""

    def __init__(self, executable: str = "tesseract") -> None:
        self.executable = executable

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
        tsv = self._run_tesseract(Path(image_path))
        return parse_tesseract_tsv(tsv, page_number=page_number)

    def extract_pdf_pages(
        self,
        pdf_path: str | Path,
        *,
        page_numbers: set[int] | None = None,
    ) -> list[TextObservation]:
        """Render selected PDF pages and OCR them into observations."""

        self.ensure_available()
        observations: list[TextObservation] = []
        with TemporaryDirectory(prefix="w2_pipeline_ocr_") as temp_dir:
            with pymupdf.open(Path(pdf_path)) as document:
                for page_index, page in enumerate(document, start=1):
                    if page_numbers is not None and page_index not in page_numbers:
                        continue
                    image_path = Path(temp_dir) / f"page_{page_index}.png"
                    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
                    pixmap.save(image_path)
                    observations.extend(self.extract_image(image_path, page_number=page_index))
        return observations

    def _run_tesseract(self, image_path: Path) -> str:
        command = [self.executable, str(image_path), "stdout", "--psm", "6", "tsv"]
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


def parse_tesseract_tsv(tsv_payload: str, *, page_number: int) -> list[TextObservation]:
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
        observations.append(
            TextObservation(
                text=text,
                page=page_number,
                bbox=BoundingBox(x0=left, y0=top, x1=left + width, y1=top + height),
                source=ObservationSource.OCR,
            )
        )
    return observations


def _parse_float(value: str | None) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _parse_confidence(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
