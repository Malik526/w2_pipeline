"""Phase 7 downstream output: FinalizedW2 -> JSON / CSV (and future adapters).

See `docs/contracts/review-and-downstream-output.md`.
"""

from w2_pipeline.downstream.adapter import OutputAdapter
from w2_pipeline.downstream.csv_output import export_csv
from w2_pipeline.downstream.errors import DownstreamError, NotAcceptedError
from w2_pipeline.downstream.finalize import finalize_document
from w2_pipeline.downstream.json_output import export_json
from w2_pipeline.downstream.models import FinalizedW2

__all__ = [
    "DownstreamError",
    "FinalizedW2",
    "NotAcceptedError",
    "OutputAdapter",
    "export_csv",
    "export_json",
    "finalize_document",
]
