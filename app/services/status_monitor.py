"""Device status monitoring service.

Handles:
- Periodic health checks via APScheduler
- NAS: SSH ping or HTTP health endpoint
- ESP32: Heartbeat timeout detection (passive)
- Update device.status and device.last_seen_at
- Trigger notifications on offline detection
- Configurable check interval and offline threshold
"""
