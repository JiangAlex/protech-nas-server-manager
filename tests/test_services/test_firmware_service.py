"""Tests for firmware_service functions."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import DeviceType
from app.schemas.firmware import FirmwareCreate, FirmwareUpdate
from app.services import firmware_service


@pytest_asyncio.fixture
async def device_type(db_session: AsyncSession):
    """A device type for firmware tests."""
    dt = DeviceType(name="fw-svc", display_name="FW Svc")
    db_session.add(dt)
    await db_session.flush()
    await db_session.refresh(dt)
    return dt


@pytest.mark.asyncio
async def test_get_firmware_list(db_session: AsyncSession, device_type: DeviceType):
    """get_firmware_list returns all firmware."""
    await firmware_service.create_firmware(
        db_session, FirmwareCreate(device_type_id=device_type.id, version="1.0.0")
    )
    await firmware_service.create_firmware(
        db_session, FirmwareCreate(device_type_id=device_type.id, version="2.0.0")
    )
    result = await firmware_service.get_firmware_list(db_session)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_firmware_list_filter_by_type(db_session: AsyncSession, device_type: DeviceType):
    """get_firmware_list filters by device_type_id."""
    other_dt = DeviceType(name="other-fw", display_name="Other FW")
    db_session.add(other_dt)
    await db_session.flush()

    await firmware_service.create_firmware(
        db_session, FirmwareCreate(device_type_id=device_type.id, version="1.0.0")
    )
    await firmware_service.create_firmware(
        db_session, FirmwareCreate(device_type_id=other_dt.id, version="9.0.0")
    )
    result = await firmware_service.get_firmware_list(db_session, device_type_id=device_type.id)
    assert len(result) == 1
    assert result[0].version == "1.0.0"


@pytest.mark.asyncio
async def test_create_firmware_generates_version_display(db_session: AsyncSession, device_type: DeviceType):
    """create_firmware generates version_display from version + git_hash_short."""
    result = await firmware_service.create_firmware(
        db_session,
        FirmwareCreate(
            device_type_id=device_type.id,
            version="1.0.0",
            git_hash="abcdef123456",
            git_hash_short="abcdef1",
        ),
    )
    assert result.version_display == "1.0.0-abcdef1"


@pytest.mark.asyncio
async def test_create_firmware_sets_released_at(db_session: AsyncSession, device_type: DeviceType):
    """create_firmware sets released_at timestamp."""
    result = await firmware_service.create_firmware(
        db_session,
        FirmwareCreate(device_type_id=device_type.id, version="1.0.0"),
    )
    assert result.released_at is not None


@pytest.mark.asyncio
async def test_create_firmware_auto_unmarks_latest(db_session: AsyncSession, device_type: DeviceType):
    """Creating firmware with is_latest=True unmarks previous latest."""
    fw1 = await firmware_service.create_firmware(
        db_session,
        FirmwareCreate(device_type_id=device_type.id, version="1.0.0", is_latest=True),
    )
    fw2 = await firmware_service.create_firmware(
        db_session,
        FirmwareCreate(device_type_id=device_type.id, version="2.0.0", is_latest=True),
    )
    await db_session.flush()

    await db_session.refresh(fw1)
    await db_session.refresh(fw2)
    assert fw1.is_latest is False
    assert fw2.is_latest is True


@pytest.mark.asyncio
async def test_get_firmware(db_session: AsyncSession, device_type: DeviceType):
    """get_firmware returns firmware by id."""
    created = await firmware_service.create_firmware(
        db_session, FirmwareCreate(device_type_id=device_type.id, version="3.0.0")
    )
    result = await firmware_service.get_firmware(db_session, created.id)
    assert result is not None
    assert result.version == "3.0.0"


@pytest.mark.asyncio
async def test_get_firmware_not_found(db_session: AsyncSession):
    """get_firmware returns None for unknown id."""
    result = await firmware_service.get_firmware(db_session, 99999)
    assert result is None


@pytest.mark.asyncio
async def test_get_firmware_by_version(db_session: AsyncSession, device_type: DeviceType):
    """get_firmware_by_version returns firmware by type+version."""
    await firmware_service.create_firmware(
        db_session, FirmwareCreate(device_type_id=device_type.id, version="4.0.0")
    )
    result = await firmware_service.get_firmware_by_version(
        db_session, device_type.id, "4.0.0"
    )
    assert result is not None
    assert result.version == "4.0.0"


@pytest.mark.asyncio
async def test_update_firmware(db_session: AsyncSession, device_type: DeviceType):
    """update_firmware updates fields."""
    created = await firmware_service.create_firmware(
        db_session,
        FirmwareCreate(device_type_id=device_type.id, version="5.0.0", changelog="Old"),
    )
    data = FirmwareUpdate(changelog="New changelog")
    result = await firmware_service.update_firmware(db_session, created.id, data)
    assert result is not None
    assert result.changelog == "New changelog"


@pytest.mark.asyncio
async def test_update_firmware_not_found(db_session: AsyncSession):
    """update_firmware returns None for unknown id."""
    result = await firmware_service.update_firmware(
        db_session, 99999, FirmwareUpdate(changelog="Whatever")
    )
    assert result is None


@pytest.mark.asyncio
async def test_delete_firmware(db_session: AsyncSession, device_type: DeviceType):
    """delete_firmware removes firmware and returns True."""
    created = await firmware_service.create_firmware(
        db_session, FirmwareCreate(device_type_id=device_type.id, version="6.0.0")
    )
    result = await firmware_service.delete_firmware(db_session, created.id)
    assert result is True
    fetched = await firmware_service.get_firmware(db_session, created.id)
    assert fetched is None


@pytest.mark.asyncio
async def test_mark_as_latest(db_session: AsyncSession, device_type: DeviceType):
    """mark_as_latest sets is_latest=True and unmarks others."""
    fw1 = await firmware_service.create_firmware(
        db_session,
        FirmwareCreate(device_type_id=device_type.id, version="7.0.0", is_latest=True),
    )
    fw2 = await firmware_service.create_firmware(
        db_session,
        FirmwareCreate(device_type_id=device_type.id, version="8.0.0"),
    )
    await db_session.flush()

    result = await firmware_service.mark_as_latest(db_session, fw2.id)
    assert result.is_latest is True

    await db_session.refresh(fw1)
    assert fw1.is_latest is False


@pytest.mark.asyncio
async def test_mark_as_stable(db_session: AsyncSession, device_type: DeviceType):
    """mark_as_stable sets is_stable=True."""
    created = await firmware_service.create_firmware(
        db_session, FirmwareCreate(device_type_id=device_type.id, version="9.0.0")
    )
    result = await firmware_service.mark_as_stable(db_session, created.id)
    assert result.is_stable is True
