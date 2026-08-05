"""OTA API endpoints for ESP32 and other firmware devices.

- GET  /api/ota/{device_type}/check   - Device checks for new version
- POST /api/ota/{device_type}/report  - Device reports update result

Authentication: X-Device-Token header
"""
