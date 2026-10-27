"""Unit test cho Bước 16 – xoay vòng bản sao lưu và checksum (không cần Docker)."""

import hashlib

import pytest

from src.ops import backup


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "backup_root", lambda: tmp_path)
    return tmp_path


def test_rotate_keeps_newest_complete_backups(root):
    names = [f"202610{d:02d}T070000" for d in range(1, 8)]
    for n in names:
        (root / n).mkdir()
        (root / n / "manifest.json").write_text("{}")
    (root / "20261031T070000").mkdir()          # bản dở dang (chưa có manifest): không tính, không xóa
    removed = backup.rotate()
    keep = backup.config.settings()["backup"]["keep"]
    assert sorted(p.name for p in removed) == names[:-keep]
    remaining = sorted(p.name for p in root.iterdir())
    assert remaining == names[-keep:] + ["20261031T070000"]


def test_sha256_matches_hashlib(tmp_path):
    f = tmp_path / "a.bin"
    data = b"x" * 3_000_000                       # > 1 MB để đi qua nhiều chunk
    f.write_bytes(data)
    assert backup.sha256(f) == hashlib.sha256(data).hexdigest()
