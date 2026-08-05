"""APScheduler configuration for periodic tasks.

Scheduled jobs:
- Health check: Runs every N seconds, checks all active devices
- Offline detection: Evaluates last_seen_at vs threshold
- (Optional) Auto-update: Check for new versions and notify
"""
