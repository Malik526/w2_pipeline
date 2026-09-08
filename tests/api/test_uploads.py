"""Phase 8D.7: upload-staging safety tests.

Covers the filename -> document ID sanitization that closes path
traversal at the source, before any FastAPI route or filesystem join
ever sees a raw uploaded filename.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from w2_pipeline.api.uploads import UnsupportedUploadError, stage_uploads, supported_extensions


def test_supported_extensions_matches_ingestion() -> None:
    assert set(supported_extensions()) == {".pdf", ".jpg", ".jpeg", ".png"}


def test_stage_uploads_writes_files_and_returns_document_ids(tmp_path: Path) -> None:
    staged = stage_uploads(
        [("w2_one.png", b"one"), ("w2_two.pdf", b"two")], destination_dir=tmp_path / "run"
    )

    assert [item.document_id for item in staged] == ["w2_one", "w2_two"]
    assert staged[0].path.read_bytes() == b"one"
    assert staged[1].path.read_bytes() == b"two"
    assert staged[0].original_filename == "w2_one.png"


def test_stage_uploads_rejects_unsupported_extension(tmp_path: Path) -> None:
    with pytest.raises(UnsupportedUploadError):
        stage_uploads([("notes.txt", b"hello")], destination_dir=tmp_path / "run")


def test_stage_uploads_rejects_whole_batch_if_any_file_unsupported(tmp_path: Path) -> None:
    """No partial staging: a mixed valid/invalid batch stages nothing."""

    destination = tmp_path / "run"
    with pytest.raises(UnsupportedUploadError):
        stage_uploads([("good.png", b"ok"), ("bad.exe", b"no")], destination_dir=destination)

    assert not destination.exists()


def test_stage_uploads_strips_path_traversal_from_filename(tmp_path: Path) -> None:
    destination = tmp_path / "run"
    staged = stage_uploads([("../../etc/passwd.png", b"x")], destination_dir=destination)

    assert len(staged) == 1
    document_id = staged[0].document_id
    assert "/" not in document_id and ".." not in document_id
    # The staged file must land strictly inside the destination directory.
    assert staged[0].path.resolve().parent == destination.resolve()


def test_stage_uploads_disambiguates_colliding_document_ids(tmp_path: Path) -> None:
    staged = stage_uploads(
        [("w2.png", b"a"), ("w2.png", b"b"), ("../w2.jpg", b"c")], destination_dir=tmp_path / "run"
    )

    document_ids = [item.document_id for item in staged]
    assert len(document_ids) == len(set(document_ids))
    assert document_ids[0] == "w2"


def test_stage_uploads_document_id_charset_is_always_safe(tmp_path: Path) -> None:
    staged = stage_uploads(
        [("weird name!!.png", b"x"), ("  .pdf", b"y")], destination_dir=tmp_path / "run"
    )

    for item in staged:
        assert all(char.isalnum() or char in "_-" for char in item.document_id)
        assert item.document_id != ""
