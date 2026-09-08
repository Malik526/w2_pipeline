"""Phase 8D.7: demo UI FastAPI endpoint tests.

Mocks at the application-service boundary (`w2_pipeline.api.service.run_document`/
`run_batch`), exactly as `tests/cli/test_run_document_cli.py` mocks
`w2_pipeline.cli.run_document.run_document` -- no OCR/GPU dependency,
and no re-testing of `run_document()`/`run_batch()` orchestration itself
(already covered by `tests/application/`). These tests check only this
API layer's own responsibilities: upload handling, single-vs-batch
routing, response shaping, download safety, and the shared-extractor
lock/lifecycle.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from w2_pipeline.api import service
from w2_pipeline.application.run_batch import BatchRunResult
from w2_pipeline.application.run_document import DocumentRunResult, DocumentRunStatus

_PNG_BYTES = b"not-a-real-image-but-thats-fine-for-these-mocks"


def _accepted_result(document_id: str, output_dir: Path) -> DocumentRunResult:
    doc_dir = output_dir / document_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / "final.json").write_text(
        json.dumps({"document_id": document_id, "status": "accepted", "schema_version": 2026, "tax_year": 2026, "document": {"metadata": {"document_id": document_id}}}),
        encoding="utf-8",
    )
    (doc_dir / "final.csv").write_text("metadata.document_id\n" + document_id + "\n", encoding="utf-8")
    return DocumentRunResult(
        status=DocumentRunStatus.ACCEPTED,
        document_id=document_id,
        input_file=f"{document_id}.png",
        output_dir=str(doc_dir),
        pipeline_id="pipeline_a",
        ocr_backend="paddleocr",
        route="ocr",
        validation_status="accepted",
        issue_codes=[],
        review_id=None,
        finalized=True,
        outputs={"json": str(doc_dir / "final.json"), "csv": str(doc_dir / "final.csv")},
        model_startup_seconds=0.01,
        processing_latency_seconds=1.2,
        total_duration_seconds=1.21,
    )


def _needs_review_result(document_id: str, output_dir: Path) -> DocumentRunResult:
    return DocumentRunResult(
        status=DocumentRunStatus.NEEDS_REVIEW,
        document_id=document_id,
        input_file=f"{document_id}.png",
        output_dir=str(output_dir / document_id),
        pipeline_id="pipeline_a",
        ocr_backend="paddleocr",
        route="ocr",
        validation_status="needs_review",
        issue_codes=["employer_address_extraction_incomplete"],
        review_id="11111111-1111-1111-1111-111111111111",
        finalized=False,
        outputs={},
        model_startup_seconds=0.01,
        processing_latency_seconds=1.3,
        total_duration_seconds=1.31,
    )


def _upload_files(names: list[str]) -> list[tuple[str, tuple[str, bytes, str]]]:
    return [("files", (name, _PNG_BYTES, "image/png")) for name in names]


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert set(body["supported_extensions"]) == {".pdf", ".jpg", ".jpeg", ".png"}


def test_single_file_upload_calls_run_document_only(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, output_root: Path
) -> None:
    calls: list[str] = []

    def fake_run_document(input_file, *, output_dir, document_id, review_repo_dir, extractor):  # noqa: ANN001
        calls.append("run_document")
        return _accepted_result(document_id, Path(output_dir))

    def fake_run_batch(*args, **kwargs):  # noqa: ANN001
        raise AssertionError("run_batch must not be called for a single-file upload")

    monkeypatch.setattr(service, "run_document", fake_run_document)
    monkeypatch.setattr(service, "run_batch", fake_run_batch)
    monkeypatch.setattr(service, "_get_shared_extractor", lambda: object())

    response = client.post("/api/process", files=_upload_files(["w2_one.png"]))

    assert response.status_code == 200
    body = response.json()
    assert calls == ["run_document"]
    assert body["mode"] == "single"
    assert body["documents_total"] == 1
    assert body["accepted"] == 1
    assert body["documents"][0]["filename"] == "w2_one.png"
    assert body["documents"][0]["downloads"] == {
        "json": f"/api/runs/{body['run_id']}/documents/w2_one/final.json",
        "csv": f"/api/runs/{body['run_id']}/documents/w2_one/final.csv",
    }


def test_multi_file_upload_calls_run_batch_once_only(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, output_root: Path
) -> None:
    batch_calls: list[list[str]] = []

    def fake_run_batch(input_files, *, output_dir, review_repo_dir, extractor):  # noqa: ANN001
        batch_calls.append([Path(f).name for f in input_files])
        documents = [
            _accepted_result("doc_a", Path(output_dir)),
            _needs_review_result("doc_b", Path(output_dir)),
        ]
        return BatchRunResult(
            pipeline_id="pipeline_a",
            ocr_backend="paddleocr",
            device="gpu",
            documents_total=2,
            accepted=1,
            needs_review=1,
            failed=0,
            model_startup_seconds=5.0,
            batch_processing_seconds=2.5,
            total_duration_seconds=7.5,
            mean_document_latency_seconds=1.25,
            median_document_latency_seconds=1.25,
            aggregate_csv=str(Path(output_dir) / "batch_finalized.csv"),
            documents=documents,
        )

    def fake_run_document(*args, **kwargs):  # noqa: ANN001
        raise AssertionError("run_document must not be called for a multi-file upload")

    output_root.mkdir(parents=True, exist_ok=True)

    # Wraps `fake_run_batch` to also write the aggregate CSV it claims
    # exists, keyed off `output_dir` (the run ID is only known once
    # `/api/process` generates it, so this can't be pre-created by the
    # test itself).
    def fake_run_batch_with_csv(input_files, *, output_dir, review_repo_dir, extractor):  # noqa: ANN001
        result = fake_run_batch(input_files, output_dir=output_dir, review_repo_dir=review_repo_dir, extractor=extractor)
        Path(result.aggregate_csv).write_text("metadata.document_id\ndoc_a\n", encoding="utf-8")
        return result

    monkeypatch.setattr(service, "run_document", fake_run_document)
    monkeypatch.setattr(service, "run_batch", fake_run_batch_with_csv)
    monkeypatch.setattr(service, "_get_shared_extractor", lambda: object())

    response = client.post("/api/process", files=_upload_files(["doc_a.png", "doc_b.png"]))

    assert response.status_code == 200
    body = response.json()
    assert len(batch_calls) == 1
    assert body["mode"] == "batch"
    assert body["documents_total"] == 2
    assert body["accepted"] == 1
    assert body["needs_review"] == 1
    assert body["aggregate_csv_available"] is True
    assert body["aggregate_csv_url"] == f"/api/runs/{body['run_id']}/batch.csv"

    needs_review_doc = next(d for d in body["documents"] if d["document_id"] == "doc_b")
    assert needs_review_doc["downloads"] == {}
    assert needs_review_doc["review_id"] == "11111111-1111-1111-1111-111111111111"


def test_needs_review_download_blocked(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, output_root: Path
) -> None:
    monkeypatch.setattr(
        service, "run_document", lambda input_file, **kwargs: _needs_review_result(kwargs["document_id"], Path(kwargs["output_dir"]))
    )
    monkeypatch.setattr(service, "_get_shared_extractor", lambda: object())

    response = client.post("/api/process", files=_upload_files(["review_me.png"]))
    run_id = response.json()["run_id"]

    for artifact in ("final.json", "final.csv"):
        download = client.get(f"/api/runs/{run_id}/documents/review_me/{artifact}")
        assert download.status_code == 404


def test_accepted_download_returns_real_file_content(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        service, "run_document", lambda input_file, **kwargs: _accepted_result(kwargs["document_id"], Path(kwargs["output_dir"]))
    )
    monkeypatch.setattr(service, "_get_shared_extractor", lambda: object())

    response = client.post("/api/process", files=_upload_files(["good.png"]))
    run_id = response.json()["run_id"]

    json_download = client.get(f"/api/runs/{run_id}/documents/good/final.json")
    assert json_download.status_code == 200
    assert json_download.json()["document_id"] == "good"

    csv_download = client.get(f"/api/runs/{run_id}/documents/good/final.csv")
    assert csv_download.status_code == 200
    assert "good" in csv_download.text


def test_document_detail_exposes_canonical_data(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        service, "run_document", lambda input_file, **kwargs: _accepted_result(kwargs["document_id"], Path(kwargs["output_dir"]))
    )
    monkeypatch.setattr(service, "_get_shared_extractor", lambda: object())

    response = client.post("/api/process", files=_upload_files(["good.png"]))
    run_id = response.json()["run_id"]

    detail = client.get(f"/api/runs/{run_id}/documents/good")
    assert detail.status_code == 200
    body = detail.json()
    assert body["canonical"]["metadata"]["document_id"] == "good"


def test_unsupported_upload_returns_400(client: TestClient) -> None:
    response = client.post("/api/process", files=[("files", ("notes.txt", b"hello", "text/plain"))])
    assert response.status_code == 400


def test_no_files_rejected(client: TestClient) -> None:
    # FastAPI's own request validation rejects a wholly-missing required
    # `files` field with 422 before this endpoint's own `if not files`
    # guard ever runs; both are "no files were uploaded" from the
    # caller's perspective.
    response = client.post("/api/process", files=[])
    assert response.status_code in (400, 422)


def test_shared_extractor_cold_start_is_reported_at_run_level(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: the shared extractor's own build/warm_up cost happens
    *before* `run_document()`/`run_batch()` start their own timers, so
    those functions always see an already-warm extractor and report
    near-zero `model_startup_seconds` themselves. That real cold-start
    cost must still surface somewhere in the response -- at the run
    level -- rather than being silently absorbed into the request's
    wall time and never reported at all."""

    def slow_get_shared_extractor():
        time.sleep(0.05)
        return object()

    monkeypatch.setattr(service, "_get_shared_extractor", slow_get_shared_extractor)
    monkeypatch.setattr(
        service, "run_document", lambda input_file, **kwargs: _accepted_result(kwargs["document_id"], Path(kwargs["output_dir"]))
    )

    response = client.post("/api/process", files=_upload_files(["good.png"]))

    body = response.json()
    assert body["model_startup_seconds"] >= 0.05
    assert body["total_duration_seconds"] >= body["model_startup_seconds"]


def test_processor_unavailable_returns_502(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise():
        raise RuntimeError("simulated missing OCR dependency")

    monkeypatch.setattr(service, "_get_shared_extractor", _raise)

    response = client.post("/api/process", files=_upload_files(["good.png"]))

    assert response.status_code == 502


def test_invalid_run_id_and_document_id_rejected(client: TestClient) -> None:
    assert client.get("/api/runs/not-a-valid-run-id").status_code == 400
    assert client.get("/api/runs/" + "a" * 32 + "/documents/../secret").status_code in (400, 404)
    assert client.get("/api/runs/" + "a" * 32).status_code == 404


def test_unknown_run_returns_404(client: TestClient) -> None:
    assert client.get("/api/runs/" + "0" * 32).status_code == 404


def test_two_uploads_get_isolated_run_and_output_dirs(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, output_root: Path
) -> None:
    monkeypatch.setattr(
        service, "run_document", lambda input_file, **kwargs: _accepted_result(kwargs["document_id"], Path(kwargs["output_dir"]))
    )
    monkeypatch.setattr(service, "_get_shared_extractor", lambda: object())

    first = client.post("/api/process", files=_upload_files(["a.png"])).json()
    second = client.post("/api/process", files=_upload_files(["a.png"])).json()

    assert first["run_id"] != second["run_id"]
    assert (output_root / first["run_id"]).exists()
    assert (output_root / second["run_id"]).exists()


def test_concurrent_processing_returns_409_busy(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = threading.Event()
    release = threading.Event()

    def slow_run_document(input_file, *, output_dir, document_id, review_repo_dir, extractor):  # noqa: ANN001
        started.set()
        release.wait(timeout=5)
        return _accepted_result(document_id, Path(output_dir))

    monkeypatch.setattr(service, "run_document", slow_run_document)
    monkeypatch.setattr(service, "_get_shared_extractor", lambda: object())

    results: dict[str, int] = {}

    def _first_request() -> None:
        results["first"] = client.post("/api/process", files=_upload_files(["a.png"])).status_code

    thread = threading.Thread(target=_first_request)
    thread.start()
    assert started.wait(timeout=5)
    time.sleep(0.05)  # let the first request settle inside the lock

    second_status = client.post("/api/process", files=_upload_files(["b.png"])).status_code
    release.set()
    thread.join(timeout=5)

    assert second_status == 409
    assert results["first"] == 200
