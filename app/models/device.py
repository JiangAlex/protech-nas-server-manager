"""Device and DeviceType ORM models.

Tables:
- device_types: Defines device categories (nas, esp32, etc.)
  Columns: id, name, display_name, update_method, health_check_method, config (JSON)
- devices: Individual device instances
  Columns: id, device_type_id, name, description, is_active,
           current_version, current_git_hash, ip_address,
           ssh_host, ssh_port, ssh_user,
           last_seen_at, last_update_at, status, config (JSON)
"""
