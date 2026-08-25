"""Tests for artifact_service functions.

Patches get_artifacts_dir() to return a temp directory so tests don't touch /app.
"""

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def temp_artifacts_dir(tmp_path):
    """Return a temp directory for artifact storage."""
    return tmp_path / "artifacts"


def _mock_get_artifacts_dir(temp_dir):
    """Return a get_artifacts_dir that returns temp_dir."""
    def _inner():
        return temp_dir
    return _inner


@pytest.mark.asyncio
async def test_save_and_check_artifact(temp_artifacts_dir):
    """save_artifact writes file and returns checksum + size."""
    with patch("app.services.artifact_service.get_artifacts_dir", _mock_get_artifacts_dir(temp_artifacts_dir)):
        from app.services import artifact_service
        content = b"test artifact content " * 100
        checksum, size = await artifact_service.save_artifact("v1.0.0", content)
        expected = hashlib.sha256(content).hexdigest()
        assert checksum == expected
        assert size == len(content)
        assert (temp_artifacts_dir / "v1.0.0" / "frontend.tar.gz").exists()


@pytest.mark.asyncio
async def test_artifact_exists(temp_artifacts_dir):
    """artifact_exists returns True for saved artifact, False otherwise."""
    with patch("app.services.artifact_service.get_artifacts_dir", _mock_get_artifacts_dir(temp_artifacts_dir)):
        from app.services import artifact_service
        await artifact_service.save_artifact("v2.0.0", b"data")
        assert artifact_service.artifact_exists("v2.0.0") is True
        assert artifact_service.artifact_exists("never-saved") is False


@pytest.mark.asyncio
async def test_get_artifact_checksum(temp_artifacts_dir):
    """get_artifact_checksum returns SHA256 hex of existing file."""
    with patch("app.services.artifact_service.get_artifacts_dir", _mock_get_artifacts_dir(temp_artifacts_dir)):
        from app.services import artifact_service
        content = b"checksum test"
        await artifact_service.save_artifact("v4.0.0", content)
        checksum = artifact_service.get_artifact_checksum("v4.0.0")
        expected = hashlib.sha256(content).hexdigest()
        assert checksum == expected


def test_get_artifact_checksum_missing(temp_artifacts_dir):
    """get_artifact_checksum returns None for missing artifact."""
    with patch("app.services.artifact_service.get_artifacts_dir", _mock_get_artifacts_dir(temp_artifacts_dir)):
        from app.services import artifact_service
        assert artifact_service.get_artifact_checksum("missing") is None


@pytest.mark.asyncio
async def test_list_artifact_versions(temp_artifacts_dir):
    """list_artifact_versions returns sorted list of versions with artifacts."""
    with patch("app.services.artifact_service.get_artifacts_dir", _mock_get_artifacts_dir(temp_artifacts_dir)):
        from app.services import artifact_service
        for v in ["v1.0.0", "v2.0.0"]:
            await artifact_service.save_artifact(v, b"data")
        versions = artifact_service.list_artifact_versions()
        assert versions == ["v1.0.0", "v2.0.0"]


@pytest.mark.asyncio
async def test_delete_artifact(temp_artifacts_dir):
    """delete_artifact removes the artifact directory and returns True."""
    with patch("app.services.artifact_service.get_artifacts_dir", _mock_get_artifacts_dir(temp_artifacts_dir)):
        from app.services import artifact_service
        await artifact_service.save_artifact("v5.0.0", b"to delete")
        result = artifact_service.delete_artifact("v5.0.0")
        assert result is True
        assert not (temp_artifacts_dir / "v5.0.0").exists()


def test_delete_artifact_missing(temp_artifacts_dir):
    """delete_artifact returns False for missing version."""
    with patch("app.services.artifact_service.get_artifacts_dir", _mock_get_artifacts_dir(temp_artifacts_dir)):
        from app.services import artifact_service
        result = artifact_service.delete_artifact("nonexistent")
        assert result is False
