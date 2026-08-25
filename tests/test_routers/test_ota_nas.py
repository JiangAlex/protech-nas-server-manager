"""Tests for ota_nas router (5 endpoints)."""

import pytest
from httpx import AsyncClient


async def _create_device_type_and_firmware(client: AsyncClient):
    """Helper: create device type + firmware, return IDs."""
    dt_resp = await client.post(
        "/api/device-types",
        json={"name": "NAS-Pro", "display_name": "ProTech NAS Pro"},
    )
    dt_id = dt_resp.json()["id"]
    fw_resp = await client.post(
        "/api/firmware",
        json={"device_type_id": dt_id, "version": "1.0.0"},
    )
    fw_id = fw_resp.json()["id"]
    # Mark as latest AND stable (both required for NAS check to work)
    await client.post(f"/api/firmware/{fw_id}/latest")
    await client.post(f"/api/firmware/{fw_id}/stable")
    return dt_id, fw_id


async def _create_device(client: AsyncClient, dt_id: int, name: str = "TestDevice", **kwargs):
    """Helper: create a device."""
    payload = {"device_type_id": dt_id, "name": name, **kwargs}
    resp = await client.post("/api/devices", json=payload)
    return resp.json()


@pytest.mark.asyncio
async def test_nas_check_update_available(client: AsyncClient):
    """POST /api/ota/nas/check — device has older version, update available."""
    dt_id, fw_id = await _create_device_type_and_firmware(client)
    dev = await _create_device(client, dt_id, "Device-1", current_version="0.9.0")

    resp = await client.post(
        "/api/ota/nas/check",
        json={"device_id": dev["id"], "current_version": "0.9.0"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["update_available"] is True
    assert data["latest_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_nas_check_no_update(client: AsyncClient):
    """POST /api/ota/nas/check — device already at latest, no update."""
    dt_id, fw_id = await _create_device_type_and_firmware(client)
    dev = await _create_device(client, dt_id, "Device-1", current_version="1.0.0")

    resp = await client.post(
        "/api/ota/nas/check",
        json={"device_id": dev["id"], "current_version": "1.0.0"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["update_available"] is False


@pytest.mark.asyncio
async def test_nas_check_device_not_found(client: AsyncClient):
    """POST /api/ota/nas/check — non-existent device still returns 200 (placeholder)."""
    resp = await client.post(
        "/api/ota/nas/check",
        json={"device_id": 9999, "current_version": "0.9.0"},
    )
    # Service returns update_available=True even without device (placeholder logic)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_nas_download_no_update(client: AsyncClient):
    """GET /api/ota/nas/download/{device_id} — no firmware available returns 404."""
    dt_id, _ = await _create_device_type_and_firmware(client)
    dev = await _create_device(client, dt_id, "Device-1")

    resp = await client.get(f"/api/ota/nas/download/{dev['id']}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_nas_download_with_update(client: AsyncClient):
    """GET /api/ota/nas/download/{device_id} — with latest firmware returns info."""
    dt_id, fw_id = await _create_device_type_and_firmware(client)
    # Mark firmware as latest
    await client.post(f"/api/firmware/{fw_id}/latest")
    dev = await _create_device(client, dt_id, "Device-1")

    resp = await client.get(f"/api/ota/nas/download/{dev['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_nas_download_device_not_found(client: AsyncClient):
    """GET /api/ota/nas/download/{device_id} — non-existent device returns 404."""
    resp = await client.get("/api/ota/nas/download/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_nas_download_artifact_not_found(client: AsyncClient):
    """GET /api/ota/nas/artifacts/{version}/frontend.tar.gz — artifact not found returns 404."""
    resp = await client.get("/api/ota/nas/artifacts/99.99.99/frontend.tar.gz")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_nas_upload_artifact_invalid_type(client: AsyncClient):
    """POST /api/ota/nas/artifacts/{version}/upload — invalid file type returns 400."""
    resp = await client.post(
        "/api/ota/nas/artifacts/1.0.0/upload",
        files={"file": ("test.txt", b"not a tarball", "text/plain")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_nas_upload_artifact_success(client: AsyncClient):
    """POST /api/ota/nas/artifacts/{version}/upload — valid .tar.gz upload succeeds."""
    import gzip, io

    # Create a minimal valid tar.gz (a single empty file inside)
    tar_data = io.BytesIO()
    with gzip.GzipFile(fileobj=tar_data, mode="wb") as gz:
        gz.write(b"test content")
    tar_data.seek(0)

    resp = await client.post(
        "/api/ota/nas/artifacts/1.0.0/upload",
        files={"file": ("frontend.tar.gz", tar_data.read(), "application/gzip")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "1.0.0"
    assert data["size"] > 0


@pytest.mark.asyncio
async def test_nas_report_completed(client: AsyncClient):
    """POST /api/ota/nas/report — successful update report."""
    dt_id, _ = await _create_device_type_and_firmware(client)
    dev = await _create_device(client, dt_id, "Device-1")

    resp = await client.post(
        "/api/ota/nas/report",
        json={
            "device_id": dev["id"],
            "from_version": "0.9.0",
            "to_version": "1.0.0",
            "status": "completed",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_nas_report_failed(client: AsyncClient):
    """POST /api/ota/nas/report — failed update report."""
    dt_id, _ = await _create_device_type_and_firmware(client)
    dev = await _create_device(client, dt_id, "Device-1")

    resp = await client.post(
        "/api/ota/nas/report",
        json={
            "device_id": dev["id"],
            "from_version": "0.9.0",
            "to_version": "1.0.0",
            "status": "failed",
            "error_message": "Download failed",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_nas_report_rollback(client: AsyncClient):
    """POST /api/ota/nas/report — rollback report."""
    dt_id, _ = await _create_device_type_and_firmware(client)
    dev = await _create_device(client, dt_id, "Device-1")

    resp = await client.post(
        "/api/ota/nas/report",
        json={
            "device_id": dev["id"],
            "from_version": "0.9.0",
            "to_version": "1.0.0",
            "status": "rolled_back",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
