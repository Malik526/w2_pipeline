import pytest

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.synthetic import SyntheticGenerationConfig, generate_synthetic_w2_documents


@pytest.fixture
def happy_path_document() -> W2Document:
    return generate_synthetic_w2_documents(SyntheticGenerationConfig(sample_count=1))[0]
