"""Evaluation dataset and scoring harness for W-2 Pipeline."""

from w2_pipeline.evaluation.comparison import compare_w2_documents, flatten_w2_document
from w2_pipeline.evaluation.external_symage import (
    HF_DATASET_NAME,
    SYMAGE_W2_FORM_ID,
    ExternalAnnotationBundle,
    ExternalGroundTruthResult,
    SymageW2Adapter,
)
from w2_pipeline.evaluation.inputs import ExtractionInput
from w2_pipeline.evaluation.manifest import (
    BenchmarkMode,
    DatasetManifest,
    DatasetManifestEntry,
    DatasetSource,
    ExpectedQuality,
    VariantType,
    load_manifest_jsonl,
    write_manifest_jsonl,
)
from w2_pipeline.evaluation.models import (
    BenchmarkEvaluation,
    DocumentEvaluation,
    DocumentEvaluationStatus,
    EvaluationFailureKind,
    EvaluationIssue,
    FieldEvaluation,
)
from w2_pipeline.evaluation.runner import W2Extractor, evaluate_manifest
from w2_pipeline.evaluation.synthetic import (
    DEFAULT_SYNTHETIC_SEED,
    SYNTHETIC_GENERATOR_VERSION,
    SyntheticGenerationConfig,
    generate_synthetic_w2_documents,
)

__all__ = [
    "BenchmarkEvaluation",
    "BenchmarkMode",
    "DEFAULT_SYNTHETIC_SEED",
    "DatasetManifest",
    "DatasetManifestEntry",
    "DatasetSource",
    "DocumentEvaluation",
    "DocumentEvaluationStatus",
    "EvaluationFailureKind",
    "EvaluationIssue",
    "ExpectedQuality",
    "ExternalAnnotationBundle",
    "ExternalGroundTruthResult",
    "FieldEvaluation",
    "HF_DATASET_NAME",
    "SYNTHETIC_GENERATOR_VERSION",
    "SYMAGE_W2_FORM_ID",
    "SymageW2Adapter",
    "ExtractionInput",
    "SyntheticGenerationConfig",
    "VariantType",
    "W2Extractor",
    "compare_w2_documents",
    "evaluate_manifest",
    "flatten_w2_document",
    "generate_synthetic_w2_documents",
    "load_manifest_jsonl",
    "write_manifest_jsonl",
]
