"""Firmware file management service.

Handles:
- Upload .bin firmware file + compute SHA256 checksum
- Store file in ./data/firmware/{device_type}/{version}/
- Retrieve firmware metadata and download path
- Mark latest/stable versions
- Delete firmware versions
"""
