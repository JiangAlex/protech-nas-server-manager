"""Authentication for the JSON API.

- Admin API (/api/devices, /api/device-types, /api/firmware, /api/ota/batch, /api/dashboard,
  metrics, artifact upload): a logged-in web session (the admin pages call the API from the browser)
  or the X-API-Key header (ADMIN_API_KEY, for scripts). Anything else gets 401.
- Device endpoints (/api/ota/nas/*) use per-device tokens, see app/services/device_auth_service.py.
"""

import hmac

from fastapi import HTTPException, Request

from app.config import get_settings


def require_admin(request: Request) -> str:
    """FastAPI dependency: allow a logged-in admin session or a valid X-API-Key."""
    username = request.session.get("username") if "session" in request.scope else None
    if username:
        return username
    key = get_settings().admin_api_key
    presented = request.headers.get("x-api-key", "")
    if key and presented and hmac.compare_digest(presented.encode(), key.encode()):
        return "api-key"
    raise HTTPException(status_code=401, detail="Not authenticated")
