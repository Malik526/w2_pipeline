from pathlib import Path

import pytest
from PIL import Image

from w2_pipeline.extraction.pipeline_b.config import PipelineBConfig
from w2_pipeline.extraction.pipeline_b.errors import ModelLoadError, VlmInferenceError
from w2_pipeline.extraction.pipeline_b.model_runtime import QwenVlRuntime


class _FakeBatch(dict):
    def to(self, device: object) -> "_FakeBatch":
        return self


class _FakeModel:
    device = "cpu"

    def __init__(self) -> None:
        self.eval_called = False
        self.generate_calls: list[dict] = []

    def eval(self) -> None:
        self.eval_called = True

    def generate(self, **kwargs: object) -> list[list[int]]:
        self.generate_calls.append(kwargs)
        return [[1, 2, 3, 4, 5, 6]]


class _FakeProcessor:
    def __init__(self) -> None:
        self.apply_chat_template_calls: list[list[dict]] = []

    def apply_chat_template(self, messages: list[dict], **kwargs: object) -> _FakeBatch:
        self.apply_chat_template_calls.append(messages)
        return _FakeBatch({"input_ids": [[1, 2, 3]]})

    def batch_decode(self, trimmed_ids: object, **kwargs: object) -> list[str]:
        return ['{"employee": {"first_name": "Ada"}}']


class _FailingModel(_FakeModel):
    def generate(self, **kwargs: object) -> list[list[int]]:
        raise RuntimeError("cuda out of memory")


def _install_fake_transformers(monkeypatch: pytest.MonkeyPatch, *, model: object, processor: object) -> None:
    import transformers

    monkeypatch.setattr(
        transformers.Qwen3VLForConditionalGeneration,
        "from_pretrained",
        classmethod(lambda cls, *a, **k: model),
    )
    monkeypatch.setattr(
        transformers.AutoProcessor,
        "from_pretrained",
        classmethod(lambda cls, *a, **k: processor),
    )


def test_generate_returns_raw_decoded_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    model = _FakeModel()
    processor = _FakeProcessor()
    _install_fake_transformers(monkeypatch, model=model, processor=processor)

    image_path = tmp_path / "page.png"
    Image.new("RGB", (10, 10), color="white").save(image_path)

    runtime = QwenVlRuntime(config=PipelineBConfig())
    result = runtime.generate(image_path, "extraction prompt")

    assert result == '{"employee": {"first_name": "Ada"}}'
    assert model.eval_called is True
    assert len(processor.apply_chat_template_calls) == 1


def test_generate_caches_model_and_processor_across_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = _FakeModel()
    processor = _FakeProcessor()
    load_count = {"n": 0}

    import transformers

    def counting_from_pretrained(cls: object, *a: object, **k: object) -> object:
        load_count["n"] += 1
        return model

    monkeypatch.setattr(
        transformers.Qwen3VLForConditionalGeneration,
        "from_pretrained",
        classmethod(counting_from_pretrained),
    )
    monkeypatch.setattr(
        transformers.AutoProcessor, "from_pretrained", classmethod(lambda cls, *a, **k: processor)
    )

    image_path = tmp_path / "page.png"
    Image.new("RGB", (10, 10), color="white").save(image_path)

    runtime = QwenVlRuntime()
    runtime.generate(image_path, "prompt one")
    runtime.generate(image_path, "prompt two")

    assert load_count["n"] == 1
    assert runtime.load_duration_seconds is not None


def test_generate_records_gpu_diagnostics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    model = _FakeModel()
    processor = _FakeProcessor()
    _install_fake_transformers(monkeypatch, model=model, processor=processor)

    image_path = tmp_path / "page.png"
    Image.new("RGB", (10, 10), color="white").save(image_path)

    runtime = QwenVlRuntime()
    runtime.generate(image_path, "prompt")

    assert runtime.gpu_diagnostics is not None
    assert "cuda_available" in runtime.gpu_diagnostics


def test_generate_wraps_inference_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    model = _FailingModel()
    processor = _FakeProcessor()
    _install_fake_transformers(monkeypatch, model=model, processor=processor)

    image_path = tmp_path / "page.png"
    Image.new("RGB", (10, 10), color="white").save(image_path)

    runtime = QwenVlRuntime()
    with pytest.raises(VlmInferenceError, match="Qwen3-VL inference failed"):
        runtime.generate(image_path, "prompt")


def test_generate_wraps_model_load_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import transformers

    def failing_from_pretrained(cls: object, *a: object, **k: object) -> object:
        raise OSError("model repository not found")

    monkeypatch.setattr(
        transformers.Qwen3VLForConditionalGeneration,
        "from_pretrained",
        classmethod(failing_from_pretrained),
    )

    image_path = tmp_path / "page.png"
    Image.new("RGB", (10, 10), color="white").save(image_path)

    runtime = QwenVlRuntime()
    with pytest.raises(ModelLoadError, match="Failed to load"):
        runtime.generate(image_path, "prompt")


def test_generate_raises_inference_error_for_unreadable_image(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = _FakeModel()
    processor = _FakeProcessor()
    _install_fake_transformers(monkeypatch, model=model, processor=processor)

    missing_path = tmp_path / "missing.png"

    runtime = QwenVlRuntime()
    with pytest.raises(VlmInferenceError, match="Could not open prepared page image"):
        runtime.generate(missing_path, "prompt")


def test_ensure_available_raises_actionable_error_when_dependency_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins
    import sys

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "torch":
            raise ImportError("No module named 'torch'")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "torch", raising=False)
    monkeypatch.setattr(builtins, "__import__", fake_import)

    runtime = QwenVlRuntime()
    with pytest.raises(ModelLoadError, match="optional dependency group"):
        runtime.ensure_available()
