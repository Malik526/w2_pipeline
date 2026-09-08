"""Shared fixtures for the demo UI API test suite.

Every test gets an isolated uploads/output root (via monkeypatched
module constants, not the real repo paths) and a reset shared-extractor
singleton, so no test run ever touches `data/ui_uploads`/`output/ui` or
leaks a cached extractor/lock state into the next test.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from w2_pipeline.api import app as app_module
from w2_pipeline.api import service


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(app_module, "UPLOADS_ROOT", tmp_path / "uploads")
    monkeypatch.setattr(app_module, "OUTPUT_ROOT", tmp_path / "output")
    monkeypatch.setattr(app_module, "REVIEW_REPO_DIR", tmp_path / "review")
    monkeypatch.setattr(service, "_shared_extractor", None)
    assert not service._extractor_lock.locked()
    return TestClient(app_module.app)


@pytest.fixture()
def output_root(tmp_path: Path) -> Path:
    return tmp_path / "output"
