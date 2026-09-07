"""Pipeline A deterministic native-text/OCR W-2 extraction baseline."""

from __future__ import annotations

from pathlib import Path

from w2_pipeline.evaluation.inputs import ExtractionInput
from w2_pipeline.extraction.acquisition import ObservationAcquirer
from w2_pipeline.extraction.models import ExtractionResult, ExtractionWarning
from w2_pipeline.extraction.parser_2026 import (
    compute_box_12_amount_without_code_found,
    compute_employee_address_evidence,
    compute_employer_address_evidence,
    compute_employer_name_observation_count,
    parse_w2_2026_observations,
)
from w2_pipeline.ingestion import IngestionService
from w2_pipeline.ingestion.models import IngestedDocument


class PipelineAExtractor:
    """Deterministic baseline that routes native PDF text or Tesseract OCR."""

    pipeline_id = "pipeline_a"

    def __init__(
        self,
        *,
        ingestion_service: IngestionService | None = None,
        observation_acquirer: ObservationAcquirer | None = None,
    ) -> None:
        self.ingestion_service = ingestion_service or IngestionService()
        self.observation_acquirer = observation_acquirer or ObservationAcquirer()

    def warm_up(self) -> None:
        """Force the OCR backend's one-time model/client initialization now.

        Lets a caller that reuses one extractor across many documents
        (Phase 8D.5's batch runner) measure and pay backend startup cost
        exactly once, before the per-document processing loop, instead of
        attributing it to whichever document happens to run first.
        """

        self.observation_acquirer.warm_up()

    def extract_ingested(self, ingested_document: IngestedDocument) -> ExtractionResult:
        """Extract one already-ingested document into canonical W-2 output."""

        observations = self.observation_acquirer.acquire(ingested_document)
        document, warnings = parse_w2_2026_observations(
            observations,
            document_id=ingested_document.document_id,
            source_filename=ingested_document.source_filename,
            source_type=ingested_document.source_type,
        )
        return ExtractionResult(
            document=document,
            route=observations.route,
            observation_count=len(observations.observations),
            warnings=[
                *warnings,
                *[
                    ExtractionWarning(message=message)
                    for message in observations.warnings
                ],
            ],
            employer_name_observation_count=compute_employer_name_observation_count(
                document, observations.observations
            ),
            box_13_checkbox_evidence=observations.box_13_checkbox_evidence,
            box_12_amount_without_code_found=compute_box_12_amount_without_code_found(
                observations.observations
            ),
            employer_address_evidence=compute_employer_address_evidence(
                document, observations.observations
            ),
            employee_address_evidence=compute_employee_address_evidence(
                document, observations.observations
            ),
        )

    def extract(self, extraction_input: ExtractionInput) -> ExtractionResult:
        """Evaluation-runner adapter that receives annotation-free input."""

        ingested_document = self.ingestion_service.ingest(
            Path(extraction_input.document_path),
            document_id=extraction_input.document_id,
        )
        return self.extract_ingested(ingested_document)
