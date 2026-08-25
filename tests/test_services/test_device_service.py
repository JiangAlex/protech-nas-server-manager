"""Tests for device_service functions."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device, DeviceType
from app.schemas import DeviceCreate, DeviceTypeCreate, DeviceTypeUpdate, DeviceUpdate
from app.services import device_service


@pytest_asyncio.fixture
async def device_type(db_session: AsyncSession):
    """A device type for tests."""
    dt = DeviceType(name="svc-test", display_name="Svc Test")
    db_session.add(dt)
    await db_session.flush()
    await db_session.refresh(dt)
    return dt


# ── DeviceType tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_device_types(db_session: AsyncSession, device_type: DeviceType):
    """get_device_types returns all types ordered by id."""
    result = await device_service.get_device_types(db_session)
    assert len(result) == 1
    assert result[0].name == "svc-test"


@pytest.mark.asyncio
async def test_get_device_type(db_session: AsyncSession, device_type: DeviceType):
    """get_device_type returns type by id."""
    result = await device_service.get_device_type(db_session, device_type.id)
    assert result is not None
    assert result.name == "svc-test"


@pytest.mark.asyncio
async def test_get_device_type_not_found(db_session: AsyncSession):
    """get_device_type returns None for unknown id."""
    result = await device_service.get_device_type(db_session, 99999)
    assert result is None


@pytest.mark.asyncio
async def test_get_device_type_by_name(db_session: AsyncSession, device_type: DeviceType):
    """get_device_type_by_name returns type by name."""
    result = await device_service.get_device_type_by_name(db_session, "svc-test")
    assert result is not None
    assert result.id == device_type.id


@pytest.mark.asyncio
async def test_create_device_type(db_session: AsyncSession):
    """create_device_type creates and returns a new type."""
    data = DeviceTypeCreate(name="new-type", display_name="New Type")
    result = await device_service.create_device_type(db_session, data)
    assert result.name == "new-type"
    assert result.id is not None


@pytest.mark.asyncio
async def test_update_device_type(db_session: AsyncSession, device_type: DeviceType):
    """update_device_type updates fields and returns updated type."""
    data = DeviceTypeUpdate(display_name="Updated", health_check_method="tcp")
    result = await device_service.update_device_type(db_session, device_type.id, data)
    assert result is not None
    assert result.display_name == "Updated"
    assert result.health_check_method == "tcp"


@pytest.mark.asyncio
async def test_delete_device_type(db_session: AsyncSession, device_type: DeviceType):
    """delete_device_type removes the type and returns True."""
    result = await device_service.delete_device_type(db_session, device_type.id)
    assert result is True
    fetched = await device_service.get_device_type(db_session, device_type.id)
    assert fetched is None


# ── Device tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_device(db_session: AsyncSession, device_type: DeviceType):
    """create_device creates a device with default status='unknown'."""
    data = DeviceCreate(device_type_id=device_type.id, name="new-device")
    result = await device_service.create_device(db_session, data)
    assert result.name == "new-device"
    # status is not in DeviceCreate schema, defaults to "unknown" per model
    assert result.status == "unknown"


@pytest.mark.asyncio
async def test_get_devices_no_filter(db_session: AsyncSession, device_type: DeviceType):
    """get_devices returns all devices when no filter."""
    await device_service.create_device(
        db_session, DeviceCreate(device_type_id=device_type.id, name="d1")
    )
    await device_service.create_device(
        db_session, DeviceCreate(device_type_id=device_type.id, name="d2")
    )
    result = await device_service.get_devices(db_session)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_devices_filter_by_type(db_session: AsyncSession, device_type: DeviceType):
    """get_devices filters by device_type_id."""
    other_dt = DeviceType(name="other", display_name="Other")
    db_session.add(other_dt)
    await db_session.flush()

    await device_service.create_device(
        db_session, DeviceCreate(device_type_id=device_type.id, name="d1")
    )
    await device_service.create_device(
        db_session, DeviceCreate(device_type_id=other_dt.id, name="d2")
    )

    result = await device_service.get_devices(db_session, device_type_id=device_type.id)
    assert len(result) == 1
    assert result[0].name == "d1"


@pytest.mark.asyncio
async def test_get_devices_filter_by_status(db_session: AsyncSession, device_type: DeviceType):
    """get_devices filters by status."""
    # Create devices using ORM directly to set specific status values
    from app.models.device import Device
    dt1 = Device(device_type_id=device_type.id, name="d1_online", status="online")
    dt2 = Device(device_type_id=device_type.id, name="d2_offline", status="offline")
    db_session.add(dt1)
    db_session.add(dt2)
    await db_session.flush()
    result = await device_service.get_devices(db_session, status="online")
    assert len(result) == 1
    assert result[0].name == "d1_online"


@pytest.mark.asyncio
async def test_get_devices_filter_is_active(db_session: AsyncSession, device_type: DeviceType):
    """get_devices filters by is_active."""
    await device_service.create_device(
        db_session, DeviceCreate(device_type_id=device_type.id, name="active", is_active=True)
    )
    await device_service.create_device(
        db_session, DeviceCreate(device_type_id=device_type.id, name="inactive", is_active=False)
    )
    result = await device_service.get_devices(db_session, is_active=True)
    assert len(result) == 1
    assert result[0].name == "active"


@pytest.mark.asyncio
async def test_get_device(db_session: AsyncSession, device_type: DeviceType):
    """get_device returns a device with device_type loaded."""
    created = await device_service.create_device(
        db_session, DeviceCreate(device_type_id=device_type.id, name="fetch-me")
    )
    result = await device_service.get_device(db_session, created.id)
    assert result is not None
    assert result.name == "fetch-me"
    # device_type relationship should be loaded
    assert result.device_type is not None
    assert result.device_type.name == "svc-test"


@pytest.mark.asyncio
async def test_get_device_not_found(db_session: AsyncSession):
    """get_device returns None for unknown id."""
    result = await device_service.get_device(db_session, 99999)
    assert result is None


@pytest.mark.asyncio
async def test_update_device(db_session: AsyncSession, device_type: DeviceType):
    """update_device updates and returns the device."""
    created = await device_service.create_device(
        db_session, DeviceCreate(device_type_id=device_type.id, name="to-update")
    )
    # status is not in DeviceUpdate schema, so only description changes
    data = DeviceUpdate(description="New desc")
    result = await device_service.update_device(db_session, created.id, data)
    assert result is not None
    assert result.description == "New desc"


@pytest.mark.asyncio
async def test_delete_device_soft_deletes(db_session: AsyncSession, device_type: DeviceType):
    """delete_device sets is_active=False (soft delete)."""
    created = await device_service.create_device(
        db_session, DeviceCreate(device_type_id=device_type.id, name="to-delete")
    )
    result = await device_service.delete_device(db_session, created.id)
    assert result is True
    # Soft delete: get_device still returns device (no is_active filter)
    # but direct DB check shows is_active=False
    from sqlalchemy import select
    stmt = select(Device).where(Device.id == created.id)
    res = await db_session.execute(stmt)
    db_device = res.scalar_one_or_none()
    assert db_device is not None
    assert db_device.is_active is False


@pytest.mark.asyncio
async def test_get_device_count_by_status(db_session: AsyncSession, device_type: DeviceType):
    """get_device_count_by_status returns correct counts."""
    from app.models.device import Device
    # Use ORM directly to set status
    d1 = Device(device_type_id=device_type.id, name="c1", status="online")
    d2 = Device(device_type_id=device_type.id, name="c2", status="online")
    d3 = Device(device_type_id=device_type.id, name="c3", status="offline")
    db_session.add_all([d1, d2, d3])
    await db_session.flush()
    result = await device_service.get_device_count_by_status(db_session)
    assert result["total"] == 3
    assert result["online"] == 2
    assert result["offline"] == 1
