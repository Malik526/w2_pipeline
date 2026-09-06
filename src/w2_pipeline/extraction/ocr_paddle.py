"""PaddleOCR adapter for Pipeline A, evaluated as a Phase 4E alternate backend."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from w2_pipeline.extraction.errors import MissingOcrDependencyError, OcrExecutionError
from w2_pipeline.extraction.models import BoundingBox, ObservationSource, TextObservation
from w2_pipeline.extraction.pdf_rendering import rendered_pdf_pages


@dataclass(frozen=True)
class PaddleOcrConfig:
    """Configuration for Pipeline A's PaddleOCR component.

    `enable_mkldnn` defaults to False because PaddlePaddle's oneDNN CPU
    execution path raised a PIR attribute-conversion error for the PP-OCRv6
    models on the reference development machine; plain CPU inference is
    stable.
    """

    lang: str = "en"
    device: str = "cpu"
    use_doc_orientation_classify: bool = False
    use_doc_unwarping: bool = False
    use_textline_orientation: bool = False
    enable_mkldnn: bool = False


class PaddleOcrAdapter:
    """Run local PaddleOCR and convert its results into common observations."""

    def __init__(self, *, config: PaddleOcrConfig | None = None) -> None:
        self.config = config or PaddleOcrConfig()
        self._client: Any = None

    def ensure_available(self) -> None:
        """Raise an actionable error when the PaddleOCR package is missing."""

        try:
            import paddleocr  # noqa: F401
        except ImportError as exc:
            raise MissingOcrDependencyError(
                "PaddleOCR is not installed. Install the `paddle` optional "
                "dependency group (`pip install '.[paddle]'`) to enable the "
                "PaddleOCR backend."
            ) from exc

    def extract_image(self, image_path: str | Path, *, page_number: int = 1) -> list[TextObservation]:
        """OCR one image file into text observations."""

        self.ensure_available()
        observations: list[TextObservation] = []
        for payload in self._run_predict(Path(image_path)):
            texts = payload.get("rec_texts", [])
            boxes = payload.get("rec_boxes", [])
            # `rec_scores` is PaddleOCR's own native per-observation recognition
            # confidence, 0..1, parallel to `rec_texts`/`rec_boxes` (confirmed
            # against a real installed PaddleOCR 3.7.0 result, not assumed from
            # documentation). Indexed rather than zipped with texts/boxes so a
            # missing or short scores list can never drop or reorder a text
            # observation -- confidence is best-effort metadata, never a
            # condition for whether an observation exists.
            scores = payload.get("rec_scores", [])
            for index, (text, box) in enumerate(zip(texts, boxes)):
                text = text.strip()
                if not text:
                    continue
                x0, y0, x1, y1 = (float(value) for value in box)
                confidence = float(scores[index]) if index < len(scores) else None
                observations.append(
                    TextObservation(
                        text=text,
                        page=page_number,
                        bbox=BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1),
                        source=ObservationSource.OCR,
                        ocr_confidence=confidence,
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

    def _run_predict(self, image_path: Path) -> list[dict]:
        """Run the PaddleOCR pipeline and return each result's payload dict."""

        client = self._get_client()
        try:
            results = list(client.predict(str(image_path)))
        except Exception as exc:
            raise OcrExecutionError(f"PaddleOCR failed for the source document: {exc}") from exc
        return [result.json["res"] for result in results]

    def _get_client(self) -> Any:
        if self._client is None:
            from paddleocr import PaddleOCR

            self._client = PaddleOCR(
                lang=self.config.lang,
                device=self.config.device,
                use_doc_orientation_classify=self.config.use_doc_orientation_classify,
                use_doc_unwarping=self.config.use_doc_unwarping,
                use_textline_orientation=self.config.use_textline_orientation,
                enable_mkldnn=self.config.enable_mkldnn,
            )
        return self._client


def describe_paddle_gpu_availability() -> dict[str, Any]:
    """Report whether the installed PaddlePaddle runtime can use a GPU.

    A reproducible, non-benchmark diagnostic: it only queries PaddlePaddle's
    own device APIs and does not load OCR models or run inference.
    """

    try:
        import paddle
    except ImportError as exc:
        raise MissingOcrDependencyError(
            "PaddlePaddle is not installed. Install the `paddle` (CPU) or "
            "`paddlepaddle-gpu` (GPU) runtime described in "
            "docs/contracts/extraction-pipeline-a.md before checking GPU "
            "availability."
        ) from exc

    compiled_with_cuda = paddle.device.is_compiled_with_cuda()
    device_count = paddle.device.cuda.device_count() if compiled_with_cuda else 0
    device_names = [paddle.device.cuda.get_device_name(index) for index in range(device_count)]
    return {
        "paddle_version": paddle.__version__,
        "compiled_with_cuda": compiled_with_cuda,
        "cuda_device_count": device_count,
        "cuda_device_names": device_names,
    }
