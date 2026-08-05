"""Artifact storage service.

Manages frontend.tar.gz uploads and downloads for OTA updates.
Storage: /data/artifacts/{version}/frontend.tar.gz
"""

import hashlib
import os
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger()

ARTIFACTS_DIR = Path("/app/data/artifacts")


def get_artifacts_dir() -> Path:
    """Get artifacts directory, create if not exists."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACTS_DIR


def get_artifact_path(version: str, filename: str = "frontend.tar.gz") -> Path:
    """Get path for a specific artifact."""
    return get_artifacts_dir() / version / filename


def artifact_exists(version: str, filename: str = "frontend.tar.gz") -> bool:
    """Check if an artifact file exists."""
    return get_artifact_path(version, filename).is_file()


async def save_artifact(version: str, content: bytes, filename: str = "frontend.tar.gz") -> tuple[str, int]:
    """Save artifact file and return (checksum, file_size).

    Returns:
        tuple of (sha256_hex, file_size_bytes)
    """
    artifact_dir = get_artifacts_dir() / version
    artifact_dir.mkdir(parents=True, exist_ok=True)

    file_path = artifact_dir / filename
    file_path.write_bytes(content)

    # Calculate SHA256 checksum
    checksum = hashlib.sha256(content).hexdigest()
    file_size = len(content)

    logger.info(
        "artifact_saved",
        version=version,
        filename=filename,
        size=file_size,
        checksum=checksum[:12],
    )

    return checksum, file_size


def get_artifact_checksum(version: str, filename: str = "frontend.tar.gz") -> Optional[str]:
    """Calculate SHA256 checksum of an existing artifact."""
    path = get_artifact_path(version, filename)
    if not path.is_file():
        return None
    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def list_artifact_versions() -> list[str]:
    """List all versions that have artifacts."""
    artifacts_dir = get_artifacts_dir()
    if not artifacts_dir.exists():
        return []
    return sorted(
        [d.name for d in artifacts_dir.iterdir() if d.is_dir() and (d / "frontend.tar.gz").exists()]
    )


def delete_artifact(version: str) -> bool:
    """Delete artifact for a version."""
    import shutil
    artifact_dir = get_artifacts_dir() / version
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
        logger.info("artifact_deleted", version=version)
        return True
    return False
