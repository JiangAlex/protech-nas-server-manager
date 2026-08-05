"""NAS device updater via SSH + Git.

Update flow:
1. SSH connect to NAS (asyncssh, key-based auth)
2. git fetch origin
3. git checkout {target_git_hash}
4. Execute rebuild command (docker compose build + restart)
5. Verify service is healthy
6. Update device record with new version

Supports:
- Configurable rebuild command per device
- Timeout mechanism (default 300s)
- Rollback to previous git hash on failure
"""
