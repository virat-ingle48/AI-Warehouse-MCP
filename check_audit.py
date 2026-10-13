from storage.db import Database

db = Database("warehouse.db")

print("=== Recent Audit Log ===")
for entry in db.get_audit_log(limit=10):
    print(f"{entry['recorded_at']} | {entry['tool_name']} | approved={entry['approved']} | {entry['reason'] or 'OK'}")