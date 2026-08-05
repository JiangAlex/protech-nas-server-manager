"""Update log ORM model.

Table: update_logs
Columns: id, device_id, from_version, to_version, to_git_hash,
         status (pending/in_progress/completed/failed/rolled_back),
         triggered_by (admin/scheduler/device),
         error_message, started_at, completed_at
"""
