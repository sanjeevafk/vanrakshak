import os
from pathlib import Path
import pytest
from app.weights import ensure_model_weights, get_weights_dir


def test_weights_dir_creation(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "custom_weights"))
    weights_dir = get_weights_dir()
    assert weights_dir.exists()
    assert weights_dir == tmp_path / "custom_weights"


def test_ensure_model_weights_cached(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path))
    dummy_file = tmp_path / "dummy.pt"
    dummy_file.write_bytes(b"dummy_weights_content")

    result = ensure_model_weights("dummy.pt")
    assert result == dummy_file
    assert result.read_bytes() == b"dummy_weights_content"

def test_rejects_path_traversal_and_unapproved_url(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path))
    with pytest.raises(ValueError): ensure_model_weights("../escape.pt")
    with pytest.raises(ValueError): ensure_model_weights("new.pt", custom_url="http://untrusted.example/model")
