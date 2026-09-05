"""Device/dtype configuration and GPU diagnostics for Pipeline B's VLM runtime.

`device`/`dtype` default to `"auto"`, which is handed straight through to
`Qwen3VLForConditionalGeneration.from_pretrained(dtype=..., device_map=...)`
so Transformers/Accelerate resolve actual placement. `describe_gpu_availability`
is a separate, fast pre-flight diagnostic (no model load) used to inspect
real VRAM before/while loading, so Pipeline B never blindly assumes the 4B
model fits a given GPU -- mirrors the role
`w2_pipeline.extraction.ocr_paddle.describe_paddle_gpu_availability` plays
for the PaddleOCR backend.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from w2_pipeline.extraction.pipeline_b.errors import ModelLoadError

DEFAULT_MODEL_ID = "Qwen/Qwen3-VL-4B-Instruct"


@dataclass(frozen=True)
class PipelineBConfig:
    """Configuration for Pipeline B's Qwen3-VL runtime."""

    model_id: str = DEFAULT_MODEL_ID
    device: str = "auto"
    dtype: str = "auto"
    max_new_tokens: int = 2048


def describe_gpu_availability() -> dict[str, Any]:
    """Report CUDA availability and free/total VRAM without loading any model."""

    try:
        import torch
    except ImportError as exc:
        raise ModelLoadError(
            "PyTorch is not installed. Install the `vlm` optional dependency "
            "group (`pip install '.[vlm]'`) to enable Pipeline B."
        ) from exc

    cuda_available = torch.cuda.is_available()
    if not cuda_available:
        return {
            "torch_version": torch.__version__,
            "cuda_available": False,
            "device_name": None,
            "free_vram_bytes": None,
            "total_vram_bytes": None,
        }

    device_name = torch.cuda.get_device_name(0)
    free_bytes, total_bytes = torch.cuda.mem_get_info(0)
    return {
        "torch_version": torch.__version__,
        "cuda_available": True,
        "device_name": device_name,
        "free_vram_bytes": free_bytes,
        "total_vram_bytes": total_bytes,
    }
