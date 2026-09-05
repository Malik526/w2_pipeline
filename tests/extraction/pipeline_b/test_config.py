import sys
import types

import pytest

from w2_pipeline.extraction.pipeline_b.config import PipelineBConfig, describe_gpu_availability
from w2_pipeline.extraction.pipeline_b.errors import ModelLoadError


def _fake_torch_module(*, cuda_available: bool, device_name: str = "", mem_info=(0, 0)) -> types.ModuleType:
    cuda_module = types.SimpleNamespace(
        is_available=lambda: cuda_available,
        get_device_name=lambda index=0: device_name,
        mem_get_info=lambda index=0: mem_info,
    )
    module = types.ModuleType("torch")
    module.__version__ = "2.14.0+cu130"
    module.cuda = cuda_module
    return module


def test_pipeline_b_config_defaults_to_auto_device_and_dtype() -> None:
    config = PipelineBConfig()

    assert config.model_id == "Qwen/Qwen3-VL-4B-Instruct"
    assert config.device == "auto"
    assert config.dtype == "auto"
    assert config.max_new_tokens > 0


def test_describe_gpu_availability_reports_cuda_device(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        sys.modules,
        "torch",
        _fake_torch_module(
            cuda_available=True,
            device_name="NVIDIA GeForce RTX 3060",
            mem_info=(11_000_000_000, 12_000_000_000),
        ),
    )

    info = describe_gpu_availability()

    assert info == {
        "torch_version": "2.14.0+cu130",
        "cuda_available": True,
        "device_name": "NVIDIA GeForce RTX 3060",
        "free_vram_bytes": 11_000_000_000,
        "total_vram_bytes": 12_000_000_000,
    }


def test_describe_gpu_availability_reports_cpu_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "torch", _fake_torch_module(cuda_available=False))

    info = describe_gpu_availability()

    assert info["cuda_available"] is False
    assert info["device_name"] is None
    assert info["free_vram_bytes"] is None
    assert info["total_vram_bytes"] is None


def test_describe_gpu_availability_fails_clearly_when_torch_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "torch":
            raise ImportError("No module named 'torch'")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "torch", raising=False)
    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ModelLoadError, match="PyTorch is not installed"):
        describe_gpu_availability()
