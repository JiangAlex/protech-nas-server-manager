"""Firmware version ORM model.

Table: firmware_versions
Columns: id, device_type_id, version, git_hash, git_hash_short,
         version_display (v1.2.3-abc1234), changelog,
         file_path, file_size, file_checksum (SHA256),
         git_repo_url, git_branch,
         is_latest, is_stable, released_at
"""
