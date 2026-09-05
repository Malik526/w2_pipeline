"""Lazy Qwen3-VL model/processor loading and single-image inference.

This is the only module in Pipeline B that imports `torch`/`transformers`.
Model/processor loading is lazy and cached on the instance so repeated
`generate()` calls (e.g. across a benchmark run) pay the load cost once, the
same pattern `PaddleOcrAdapter._get_client` uses for its OCR client.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from PIL import Image

from w2_pipeline.extraction.pipeline_b.config import PipelineBConfig, describe_gpu_availability
from w2_pipeline.extraction.pipeline_b.errors import ModelLoadError, VlmInferenceError
from w2_pipeline.extraction.pipeline_b.prompt import build_chat_messages


class QwenVlRuntime:
    """Loads Qwen3-VL-4B-Instruct once and runs single-image, single-turn inference."""

    def __init__(self, config: PipelineBConfig | None = None) -> None:
        self.config = config or PipelineBConfig()
        self._model: Any = None
        self._processor: Any = None
        self.load_duration_seconds: float | None = None
        self.gpu_diagnostics: dict[str, Any] | None = None

    def ensure_available(self) -> None:
        """Raise an actionable error when the `vlm` dependency group is missing."""

        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
        except ImportError as exc:
            raise ModelLoadError(
                "PyTorch/Transformers are not installed. Install the `vlm` "
                "optional dependency group (`pip install '.[vlm]'`) to enable "
                "the Pipeline B Qwen3-VL backend."
            ) from exc

    def generate(self, image_path: str | Path, prompt_text: str | None = None) -> str:
        """Run one page image + extraction prompt through the model.

        Returns the model's raw decoded text response, unparsed -- JSON
        parsing and validation happen in later, separate Pipeline B stages.
        """

        model, processor = self._get_model_and_processor()

        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as exc:
            raise VlmInferenceError(
                f"Could not open prepared page image for inference: {exc}"
            ) from exc

        try:
            import torch

            messages = build_chat_messages(image, prompt_text)
            inputs = processor.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
            ).to(model.device)

            with torch.inference_mode():
                generated_ids = model.generate(**inputs, max_new_tokens=self.config.max_new_tokens)

            trimmed_ids = [
                output_ids[len(input_ids) :]
                for input_ids, output_ids in zip(inputs["input_ids"], generated_ids)
            ]
            decoded = processor.batch_decode(
                trimmed_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )
        except Exception as exc:
            raise VlmInferenceError(f"Qwen3-VL inference failed: {exc}") from exc

        return decoded[0]

    def _get_model_and_processor(self) -> tuple[Any, Any]:
        if self._model is not None and self._processor is not None:
            return self._model, self._processor

        self.ensure_available()
        self.gpu_diagnostics = describe_gpu_availability()

        try:
            from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

            started = time.perf_counter()
            model = Qwen3VLForConditionalGeneration.from_pretrained(
                self.config.model_id,
                dtype=self.config.dtype,
                device_map=self.config.device,
            )
            model.eval()
            processor = AutoProcessor.from_pretrained(self.config.model_id)
            self.load_duration_seconds = time.perf_counter() - started
        except Exception as exc:
            raise ModelLoadError(f"Failed to load {self.config.model_id!r}: {exc}") from exc

        self._model = model
        self._processor = processor
        return self._model, self._processor
