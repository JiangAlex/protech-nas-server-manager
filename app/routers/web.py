"""Web UI routes (Jinja2 server-side rendering).

All routes require session authentication.

Pages:
- GET /admin/login              - Login page
- POST /admin/login             - Process login
- GET /admin/                   - Dashboard
- GET /admin/devices/           - Device list
- GET /admin/devices/{id}/      - Device detail + operations
- GET /admin/firmware/          - Firmware management
- GET /admin/updates/           - Update history
- GET /admin/notifications/     - Notification settings
- GET /admin/device-types/      - Device type management
"""
