"""Abstract base class for notification channels.

Interface:
- send(message: str) → bool
- send_update_success(device, version)
- send_update_failure(device, error)
- send_device_offline(device, minutes)
- send_firmware_uploaded(device_type, version)
"""
