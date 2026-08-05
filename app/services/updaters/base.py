"""Abstract base class for device updaters.

Defines the DeviceUpdater interface:
- update(device, target_version, target_git_hash) → UpdateResult
- rollback(device) → UpdateResult
- check_version(device) → current version info

Each device type implements its own updater strategy.
"""
