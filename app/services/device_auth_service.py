"""Device tokens for the device endpoints (/api/ota/nas/check, download, report).

Enrollment on the first check (trust on first use):
- A device asks for a token by sending "request_token": true in its check. Old clients do not ask, so
  a token is never issued to a client that would throw it away.
- The token is issued only while the device has none. It is returned once in the check response
  (device_token); only its SHA-256 is stored. Every later request must send it in X-Device-Token.

Against a stranger using a device's id or MAC:
- A device that already has a token can never be enrolled again from the network; only an admin
  reset (POST /api/devices/{id}/token/reset) allows a new enrollment.
- A wrong token is always rejected (401), also in the transition mode.
- If the device has a MAC on record, enrollment needs the same MAC in the request.
- Requests without a valid token cannot change the MAC on record.
- DEVICE_TOKEN_ENFORCE=true also rejects requests without a token. Until then (transition, so the
  NAS clients keep working while they are updated) they are allowed and logged.

Every event of interest is written to device_auth_events with the IP, MAC and user agent:
enrolled, token_invalid, token_missing, enroll_rejected, mac_change_ignored, ok_new_ip (a valid token
from an IP not seen before), token_reset, unknown_device.
"""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.device import Device
from app.models.device_auth_event import DeviceAuthEvent

logger = structlog.get_logger()

TOKEN_HEADER = "x-device-token"


@dataclass
class AuthResult:
    authenticated: bool                 # a valid token was presented
    issued_token: Optional[str] = None  # set once, when the device was just enrolled

    @property
    def trusted(self) -> bool:
        """The request may change identity data (MAC) of the device."""
        return self.authenticated or self.issued_token is not None


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def normalize_mac(mac: Optional[str]) -> Optional[str]:
    if not mac:
        return None
    m = mac.strip().lower().replace("-", ":")
    return m or None


def client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


async def _reject(db: AsyncSession, detail: str) -> None:
    """Commit the audit rows written so far, then answer 401.

    get_db() rolls the session back when the request raises, which would also drop the log of the
    rejected attempt. Authentication runs before the endpoint changes anything, so the commit only
    contains audit rows.
    """
    await db.commit()
    raise HTTPException(status_code=401, detail=detail)


async def log_event(
    db: AsyncSession,
    request: Optional[Request],
    device_id: Optional[int],
    event: str,
    endpoint: str,
    mac: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    ua = request.headers.get("user-agent", "")[:200] if request else None
    ip = client_ip(request) if request else None
    db.add(
        DeviceAuthEvent(
            device_id=device_id,
            event=event,
            endpoint=endpoint,
            ip=ip,
            mac=normalize_mac(mac),
            user_agent=ua,
            detail=detail,
        )
    )
    await db.flush()
    log = logger.warning if event in ("token_invalid", "enroll_rejected", "mac_change_ignored") else logger.info
    log("device_auth_event", device_id=device_id, auth_event=event, endpoint=endpoint, ip=ip, detail=detail)


async def authenticate(
    db: AsyncSession,
    request: Request,
    device: Device,
    endpoint: str,
    *,
    request_token: bool = False,
    mac: Optional[str] = None,
) -> AuthResult:
    """Check the X-Device-Token of a request for `device`; enroll it when allowed.

    Raises 401 for a wrong token, and for a missing one when DEVICE_TOKEN_ENFORCE is on.
    """
    settings = get_settings()
    presented = request.headers.get(TOKEN_HEADER, "").strip()
    now = datetime.now(timezone.utc)
    ip = client_ip(request)

    if device.token_hash:
        if presented:
            if hmac.compare_digest(hash_token(presented), device.token_hash):
                if ip and ip != device.token_last_ip:
                    await log_event(db, request, device.id, "ok_new_ip", endpoint, mac,
                                    f"previous IP {device.token_last_ip or '-'}")
                device.token_last_used_at = now
                device.token_last_ip = ip
                return AuthResult(authenticated=True)
            await log_event(db, request, device.id, "token_invalid", endpoint, mac)
            await _reject(db, "Invalid device token")
        await log_event(db, request, device.id, "token_missing", endpoint, mac,
                        "enrolled device sent no token" + ("; rejected" if settings.device_token_enforce else ""))
        if request_token:
            await log_event(db, request, device.id, "enroll_rejected", endpoint, mac,
                            "device already has a token; an admin reset is needed for a new one")
        if settings.device_token_enforce:
            await _reject(db, "Device token required")
        return AuthResult(authenticated=False)

    # No token yet
    if presented:
        await log_event(db, request, device.id, "token_invalid", endpoint, mac, "device has no token")
        await _reject(db, "Invalid device token")

    if request_token:
        on_record = normalize_mac(device.mac_address)
        sent = normalize_mac(mac)
        if on_record and sent != on_record:
            await log_event(db, request, device.id, "enroll_rejected", endpoint, mac,
                            f"MAC {sent or '(none)'} does not match the MAC on record")
            if settings.device_token_enforce:
                await _reject(db, "Device token required")
            return AuthResult(authenticated=False)
        token = secrets.token_urlsafe(32)
        device.token_hash = hash_token(token)
        device.token_issued_at = now
        device.token_last_used_at = now
        device.token_last_ip = ip
        await log_event(db, request, device.id, "enrolled", endpoint, mac,
                        "token issued" + ("" if on_record else " (no MAC on record before)"))
        return AuthResult(authenticated=False, issued_token=token)

    await log_event(db, request, device.id, "token_missing", endpoint, mac,
                    "client did not ask for a token" + ("; rejected" if settings.device_token_enforce else ""))
    if settings.device_token_enforce:
        await _reject(db, "Device token required")
    return AuthResult(authenticated=False)


async def apply_mac(
    db: AsyncSession, request: Request, device: Device, mac: Optional[str], auth: AuthResult, endpoint: str
) -> None:
    """Store the MAC sent by the device. Without a valid token an existing MAC is never changed."""
    sent = normalize_mac(mac)
    if not sent:
        return
    on_record = normalize_mac(device.mac_address)
    if sent == on_record:
        return
    if on_record and not auth.trusted:
        await log_event(db, request, device.id, "mac_change_ignored", endpoint, mac,
                        f"MAC on record {on_record}; request without a valid token")
        return
    device.mac_address = sent


async def reset_token(db: AsyncSession, request: Request, device: Device, by: str) -> None:
    device.token_hash = None
    device.token_issued_at = None
    device.token_last_used_at = None
    device.token_last_ip = None
    await log_event(db, request, device.id, "token_reset", "admin", None, f"by {by}")


async def list_events(db: AsyncSession, device_id: int, limit: int = 100) -> list[DeviceAuthEvent]:
    result = await db.execute(
        select(DeviceAuthEvent)
        .where(DeviceAuthEvent.device_id == device_id)
        .order_by(DeviceAuthEvent.created_at.desc(), DeviceAuthEvent.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
