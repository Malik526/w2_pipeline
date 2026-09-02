"""Lightweight JPEG/PNG validation for the ingestion boundary."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, UnidentifiedImageError

from w2_pipeline.ingestion.errors import CorruptImageError, DocumentTypeMismatchError
from w2_pipeline.ingestion.models import ImageInspectionResult, SourceDocumentType

IMAGE_FORMAT_BY_SOURCE_TYPE = {
    SourceDocumentType.JPEG: "JPEG",
    SourceDocumentType.PNG: "PNG",
}


def inspect_image(path: str | Path, source_type: SourceDocumentType) -> ImageInspectionResult:
    """Verify a JPEG/PNG can be opened and return dimensions."""

    image_path = Path(path)
    expected_format = IMAGE_FORMAT_BY_SOURCE_TYPE[source_type]

    try:
        with Image.open(image_path) as image:
            image.verify()
        with Image.open(image_path) as image:
            actual_format = image.format
            width, height = image.size
    except (OSError, UnidentifiedImageError) as exc:
        raise CorruptImageError(f"Could not open or inspect image: {image_path.name}") from exc

    if actual_format != expected_format:
        raise DocumentTypeMismatchError(
            f"Image content does not match expected type for {image_path.name}"
        )

    return ImageInspectionResult(width_pixels=width, height_pixels=height)
