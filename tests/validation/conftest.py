import pytest

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.synthetic import SyntheticGenerationConfig, generate_synthetic_w2_documents


@pytest.fixture
def happy_path_document() -> W2Document:
    """A structurally complete, fully populated synthetic 2026 W-2.

    Sample 1 of the deterministic generator: SSN/name/EIN/employer name all
    present, Box 1/2/3/4/5/6 all populated, one valid Box 12 entry
    (`"DD"`), one state/local row -- a document every Phase 6 rule should
    accept.
    """

    return generate_synthetic_w2_documents(SyntheticGenerationConfig(sample_count=1))[0]
