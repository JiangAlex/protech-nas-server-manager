"""ESP32 OTA updater.

Unlike NAS (push-based), ESP32 uses pull-based OTA:
- Server stores firmware .bin files
- ESP32 periodically checks /api/ota/esp32/check
- If new version available, ESP32 downloads and flashes
- ESP32 reports result via /api/ota/esp32/report

This updater handles:
- Version comparison logic
- Firmware URL generation
- Update status tracking
- Optional: trigger flag for admin-initiated updates
"""
