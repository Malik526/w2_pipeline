"""Minimal deterministic W-2-like document rendering and variants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pymupdf
from PIL import Image, ImageFilter

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.manifest import ExpectedQuality, VariantType

RENDERER_VERSION = "2026.phase3.v1"


@dataclass(frozen=True)
class RenderedVariant:
    """Generated document variant metadata."""

    variant_id: str
    variant_type: VariantType
    expected_quality: ExpectedQuality
    document_path: Path
    transformation_config: dict[str, int | float | str]


def render_document_variants(
    document: W2Document,
    output_dir: str | Path,
    *,
    variant_types: tuple[VariantType, ...] = (
        VariantType.CLEAN_PDF,
        VariantType.CLEAN_PNG,
        VariantType.ROTATED_PNG,
        VariantType.COMPRESSED_JPEG,
        VariantType.BLURRED_PNG,
    ),
) -> list[RenderedVariant]:
    """Render a W-2-like source document and deterministic visual variants."""

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    sample_id = document.metadata.document_id
    clean_pdf_path = target_dir / f"{sample_id}_clean.pdf"
    clean_png_path = target_dir / f"{sample_id}_clean.png"

    if any(variant in variant_types for variant in (VariantType.CLEAN_PDF, VariantType.CLEAN_PNG)):
        render_clean_pdf(document, clean_pdf_path)
    if any(variant != VariantType.CLEAN_PDF for variant in variant_types):
        render_clean_pdf(document, clean_pdf_path)
        render_pdf_to_png(clean_pdf_path, clean_png_path)

    variants: list[RenderedVariant] = []
    for variant_type in variant_types:
        if variant_type == VariantType.CLEAN_PDF:
            variants.append(
                RenderedVariant(
                    variant_id=VariantType.CLEAN_PDF.value,
                    variant_type=variant_type,
                    expected_quality=ExpectedQuality.CLEAN,
                    document_path=clean_pdf_path,
                    transformation_config={"renderer": RENDERER_VERSION},
                )
            )
        elif variant_type == VariantType.CLEAN_PNG:
            variants.append(
                RenderedVariant(
                    variant_id=VariantType.CLEAN_PNG.value,
                    variant_type=variant_type,
                    expected_quality=ExpectedQuality.CLEAN,
                    document_path=clean_png_path,
                    transformation_config={"source": VariantType.CLEAN_PDF.value},
                )
            )
        elif variant_type == VariantType.ROTATED_PNG:
            angle = 2.0 if int(sample_id[-1]) % 2 else -2.0
            rotated_path = target_dir / f"{sample_id}_rotated.png"
            rotate_image(clean_png_path, rotated_path, angle_degrees=angle)
            variants.append(
                RenderedVariant(
                    variant_id=VariantType.ROTATED_PNG.value,
                    variant_type=variant_type,
                    expected_quality=ExpectedQuality.ROTATED,
                    document_path=rotated_path,
                    transformation_config={
                        "source": VariantType.CLEAN_PNG.value,
                        "angle_degrees": angle,
                    },
                )
            )
        elif variant_type == VariantType.COMPRESSED_JPEG:
            jpeg_path = target_dir / f"{sample_id}_compressed.jpg"
            compress_image_to_jpeg(clean_png_path, jpeg_path, quality=58)
            variants.append(
                RenderedVariant(
                    variant_id=VariantType.COMPRESSED_JPEG.value,
                    variant_type=variant_type,
                    expected_quality=ExpectedQuality.COMPRESSED,
                    document_path=jpeg_path,
                    transformation_config={
                        "source": VariantType.CLEAN_PNG.value,
                        "quality": 58,
                    },
                )
            )
        elif variant_type == VariantType.BLURRED_PNG:
            blurred_path = target_dir / f"{sample_id}_blurred.png"
            blur_and_resize_image(clean_png_path, blurred_path, blur_radius=0.7, scale=0.75)
            variants.append(
                RenderedVariant(
                    variant_id=VariantType.BLURRED_PNG.value,
                    variant_type=variant_type,
                    expected_quality=ExpectedQuality.DEGRADED,
                    document_path=blurred_path,
                    transformation_config={
                        "source": VariantType.CLEAN_PNG.value,
                        "blur_radius": 0.7,
                        "scale": 0.75,
                    },
                )
            )
    return variants


def render_clean_pdf(document: W2Document, output_path: str | Path) -> Path:
    """Render one clearly marked synthetic W-2-like PDF fixture."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    pdf = pymupdf.open()
    page = pdf.new_page(width=612, height=792)
    pdf.set_metadata(
        {
            "title": f"Synthetic W-2 Evaluation Fixture {document.metadata.document_id}",
            "author": "w2_pipeline synthetic generator",
            "subject": "Development-only W-2-like evaluation document",
            "creator": RENDERER_VERSION,
            "producer": RENDERER_VERSION,
            "creationDate": "D:20260101000000Z",
            "modDate": "D:20260101000000Z",
        }
    )

    _draw_header(page, document)
    _draw_identity_blocks(page, document)
    _draw_federal_boxes(page, document)
    _draw_repeated_boxes(page, document)
    _draw_state_local_boxes(page, document)

    pdf.save(path, garbage=4, deflate=True, no_new_id=True)
    pdf.close()
    return path


def render_pdf_to_png(pdf_path: str | Path, output_path: str | Path) -> Path:
    """Render the first PDF page to a PNG image."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = pymupdf.open(Path(pdf_path))
    page = pdf.load_page(0)
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    pixmap.save(path)
    pdf.close()
    return path


def rotate_image(source_path: str | Path, output_path: str | Path, *, angle_degrees: float) -> Path:
    """Create a modest deterministic rotated PNG variant."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as image:
        rotated = image.convert("RGB").rotate(
            angle_degrees,
            expand=True,
            fillcolor="white",
            resample=Image.Resampling.BICUBIC,
        )
        rotated.save(path, format="PNG")
    return path


def compress_image_to_jpeg(source_path: str | Path, output_path: str | Path, *, quality: int) -> Path:
    """Create a deterministic lossy JPEG variant."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as image:
        image.convert("RGB").save(path, format="JPEG", quality=quality, optimize=False)
    return path


def blur_and_resize_image(
    source_path: str | Path,
    output_path: str | Path,
    *,
    blur_radius: float,
    scale: float,
) -> Path:
    """Create a modest low-quality PNG variant."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as image:
        rgb = image.convert("RGB")
        downscaled_size = (
            max(1, int(rgb.width * scale)),
            max(1, int(rgb.height * scale)),
        )
        degraded = rgb.resize(downscaled_size, resample=Image.Resampling.BILINEAR)
        degraded = degraded.resize(rgb.size, resample=Image.Resampling.BILINEAR)
        degraded = degraded.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        degraded.save(path, format="PNG")
    return path


def _draw_header(page: pymupdf.Page, document: W2Document) -> None:
    page.insert_text((36, 34), "SYNTHETIC W-2 EVALUATION FIXTURE", fontsize=14)
    page.insert_text(
        (36, 54),
        "Development/test artifact only. Not an official IRS form. Contains no real taxpayer PII.",
        fontsize=8,
    )
    page.insert_text((430, 34), f"Tax year {document.metadata.tax_year}", fontsize=12)


def _draw_identity_blocks(page: pymupdf.Page, document: W2Document) -> None:
    employee = document.employee
    employer = document.employer
    _draw_box(
        page,
        (36, 82, 288, 214),
        "Employee",
        [
            ("SSN", employee.ssn),
            ("Name", _join([employee.first_name, employee.middle_initial, employee.last_name, employee.suffix])),
            ("Address 1", employee.address.address_line_1),
            ("Address 2", employee.address.address_line_2),
            ("City/State/ZIP", _city_state_zip(employee.address.city, employee.address.state, employee.address.postal_code)),
        ],
    )
    _draw_box(
        page,
        (324, 82, 576, 214),
        "Employer",
        [
            ("EIN", employer.ein),
            ("Name", employer.name),
            ("Control", employer.control_number),
            ("Address 1", employer.address.address_line_1),
            ("Address 2", employer.address.address_line_2),
            ("City/State/ZIP", _city_state_zip(employer.address.city, employer.address.state, employer.address.postal_code)),
        ],
    )


def _draw_federal_boxes(page: pymupdf.Page, document: W2Document) -> None:
    federal = document.federal_wages_and_taxes
    rows = [
        ("1 Wages, tips, other comp.", federal.box_1_wages_tips_other_compensation),
        ("2 Federal income tax withheld", federal.box_2_federal_income_tax_withheld),
        ("3 Social security wages", federal.box_3_social_security_wages),
        ("4 Social security tax withheld", federal.box_4_social_security_tax_withheld),
        ("5 Medicare wages and tips", federal.box_5_medicare_wages_and_tips),
        ("6 Medicare tax withheld", federal.box_6_medicare_tax_withheld),
        ("7 Social security tips", federal.box_7_social_security_tips),
        ("8 Allocated tips", federal.box_8_allocated_tips),
        ("9 Reserved", None),
        ("10 Dependent care benefits", federal.box_10_dependent_care_benefits),
        ("11 Nonqualified plans", federal.box_11_nonqualified_plans),
    ]
    _draw_box(page, (36, 236, 576, 418), "Federal boxes", rows, columns=2)


def _draw_repeated_boxes(page: pymupdf.Page, document: W2Document) -> None:
    box_12 = [(f"12 {entry.code}", entry.amount) for entry in document.box_12_entries]
    box_13 = [
        ("13 Statutory employee", _checkbox(document.box_13.statutory_employee)),
        ("13 Retirement plan", _checkbox(document.box_13.retirement_plan)),
        ("13 Third-party sick pay", _checkbox(document.box_13.third_party_sick_pay)),
    ]
    box_14 = [(f"14a {entry.label}", entry.amount if entry.amount is not None else entry.value) for entry in document.box_14_entries]
    tips = [(f"14b code {index + 1}", entry.code) for index, entry in enumerate(document.tipped_occupation_codes)]

    _draw_box(page, (36, 440, 288, 594), "Boxes 12 and 13", box_12 + box_13)
    _draw_box(page, (324, 440, 576, 594), "Boxes 14a and 14b", box_14 + tips)


def _draw_state_local_boxes(page: pymupdf.Page, document: W2Document) -> None:
    rows: list[tuple[str, object]] = []
    for index, entry in enumerate(document.state_local_entries, start=1):
        rows.extend(
            [
                (f"15.{index} State", entry.box_15_state),
                (f"15.{index} Employer state ID", entry.box_15_employer_state_id_number),
                (f"16.{index} State wages", entry.box_16_state_wages_tips_etc),
                (f"17.{index} State tax", entry.box_17_state_income_tax),
                (f"18.{index} Local wages", entry.box_18_local_wages_tips_etc),
                (f"19.{index} Local tax", entry.box_19_local_income_tax),
                (f"20.{index} Locality", entry.box_20_locality_name),
            ]
        )
    _draw_box(page, (36, 616, 576, 756), "State and local boxes", rows, columns=2)


def _draw_box(
    page: pymupdf.Page,
    rect: tuple[int, int, int, int],
    title: str,
    rows: list[tuple[str, object]],
    *,
    columns: int = 1,
) -> None:
    page.draw_rect(pymupdf.Rect(*rect), color=(0, 0, 0), width=0.8)
    page.insert_text((rect[0] + 8, rect[1] + 16), title, fontsize=9)
    if not rows:
        page.insert_text((rect[0] + 8, rect[1] + 34), "(no entries)", fontsize=8)
        return

    column_width = (rect[2] - rect[0] - 16) / columns
    for index, (label, value) in enumerate(rows):
        column = index % columns
        row = index // columns
        x = rect[0] + 8 + (column * column_width)
        y = rect[1] + 34 + (row * 15)
        page.insert_text((x, y), f"{label}: {_display(value)}", fontsize=7.5)


def _display(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _join(parts: list[str | None]) -> str:
    return " ".join(part for part in parts if part)


def _city_state_zip(city: str | None, state: str | None, postal_code: str | None) -> str:
    return _join([city, state, postal_code])


def _checkbox(value: bool) -> str:
    return "X" if value else ""
