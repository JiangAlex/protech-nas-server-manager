"""Tests for ota_nas_service functions."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device, DeviceType
from app.models.firmware import FirmwareVersion
from app.schemas.ota_nas import NASCheckRequest, NASReportRequest
from app.services import ota_nas_service


async def _insert_test_data(db_session: AsyncSession):
    """Insert test device type, firmware, and device. Returns ids dict."""
    dt = DeviceType(name="nas-svc", display_name="NAS Svc")
    db_session.add(dt)
    await db_session.flush()

    fw = FirmwareVersion(
        device_type_id=dt.id,
        version="2.0.0",
        git_hash="deadbeef",
        git_branch="main",
        is_latest=True,
        is_stable=True,
        released_at=datetime.now(timezone.utc),
    )
    db_session.add(fw)
    await db_session.flush()

    device = Device(
        device_type_id=dt.id,
        name="ota-test-device",
        status="online",
        current_version="1.0.0",
        current_git_hash="00000000",
    )
    db_session.add(device)
    await db_session.flush()
    await db_session.refresh(device)

    return {"dt_id": dt.id, "fw_id": fw.id, "device_id": device.id}


@pytest.fixture
def mock_artifact(tmp_path):
    """Patch artifact_service to use temp dir for all artifact operations."""
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    def _mock_get_artifacts_dir():
        return artifacts

    def _mock_artifact_exists(version, filename="frontend.tar.gz"):
        return (artifacts / version / filename).is_file()

    with patch("app.services.artifact_service.get_artifacts_dir", _mock_get_artifacts_dir), \
         patch("app.services.artifact_service.artifact_exists", _mock_artifact_exists):
        yield


@pytest.mark.asyncio
async def test_check_update_available(db_session: AsyncSession, mock_artifact):
    """check_update returns update_available=True when device is behind."""
    ids = await _insert_test_data(db_session)
    request = NASCheckRequest(
        device_id=ids["device_id"],
        current_version="1.0.0",
        current_git_hash="00000000",
    )
    result = await ota_nas_service.check_update(db_session, request)
    assert result.update_available is True
    assert result.latest_version == "2.0.0"
    assert result.latest_git_hash == "deadbeef"


@pytest.mark.asyncio
async def test_check_update_not_available(db_session: AsyncSession, mock_artifact):
    """check_update returns update_available=False when device is current."""
    ids = await _insert_test_data(db_session)
    request = NASCheckRequest(
        device_id=ids["device_id"],
        current_version="2.0.0",
        current_git_hash="deadbeef",
    )
    result = await ota_nas_service.check_update(db_session, request)
    assert result.update_available is False


@pytest.mark.asyncio
async def test_check_update_unknown_device(db_session: AsyncSession, mock_artifact):
    """check_update returns update_available=False for unknown device."""
    request = NASCheckRequest(device_id=99999, current_version="1.0.0")
    result = await ota_nas_service.check_update(db_session, request)
    assert result.update_available is False


@pytest.mark.asyncio
async def test_check_update_no_latest_firmware(db_session: AsyncSession, mock_artifact):
    """check_update returns update_available=False when no latest+stable firmware."""
    ids = await _insert_test_data(db_session)
    from sqlalchemy import update

    await db_session.execute(
        update(FirmwareVersion)
        .where(FirmwareVersion.id == ids["fw_id"])
        .values(is_latest=False, is_stable=False)
    )
    await db_session.flush()

    request = NASCheckRequest(device_id=ids["device_id"], current_version="1.0.0")
    result = await ota_nas_service.check_update(db_session, request)
    assert result.update_available is False


@pytest.mark.asyncio
async def test_get_download_info(db_session: AsyncSession, mock_artifact):
    """get_download_info returns update instructions."""
    ids = await _insert_test_data(db_session)
    result = await ota_nas_service.get_download_info(db_session, ids["device_id"])
    assert result is not None
    assert result.version == "2.0.0"
    assert "git checkout" in result.instructions


@pytest.mark.asyncio
async def test_get_download_info_unknown_device(db_session: AsyncSession, mock_artifact):
    """get_download_info returns None for unknown device."""
    result = await ota_nas_service.get_download_info(db_session, 99999)
    assert result is None


@pytest.mark.asyncio
async def test_report_update_completed(db_session: AsyncSession, mock_artifact):
    """report_update handles completed status and updates device version."""
    ids = await _insert_test_data(db_session)
    request = NASReportRequest(
        device_id=ids["device_id"],
        from_version="1.0.0",
        to_version="2.0.0",
        to_git_hash="deadbeef",
        status="completed",
    )
    result = await ota_nas_service.report_update(db_session, request)
    assert result.success is True
    device = await db_session.get(Device, ids["device_id"])
    assert device.current_version == "2.0.0"
    assert device.current_git_hash == "deadbeef"


@pytest.mark.asyncio
async def test_report_update_failed(db_session: AsyncSession, mock_artifact):
    """report_update handles failed status without changing version."""
    ids = await _insert_test_data(db_session)
    original_version = "1.0.0"
    request = NASReportRequest(
        device_id=ids["device_id"],
        from_version="1.0.0",
        to_version="2.0.0",
        status="failed",
        error_message="Download failed",
    )
    result = await ota_nas_service.report_update(db_session, request)
    assert result.success is True
    device = await db_session.get(Device, ids["device_id"])
    assert device.current_version == original_version


@pytest.mark.asyncio
async def test_report_update_unknown_device(db_session: AsyncSession, mock_artifact):
    """report_update returns success=False for unknown device."""
    request = NASReportRequest(
        device_id=99999,
        to_version="2.0.0",
        status="completed",
    )
    result = await ota_nas_service.report_update(db_session, request)
    assert result.success is False
