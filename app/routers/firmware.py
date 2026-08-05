"""Firmware management API endpoints.

- POST   /api/firmware/upload                          - Upload firmware file
- GET    /api/firmware                                 - List firmware versions
- GET    /api/firmware/{id}                            - Get firmware details
- DELETE /api/firmware/{id}                            - Delete firmware version
- GET    /firmware/{device_type}/{version}/firmware.bin - Download firmware (for OTA)
"""
