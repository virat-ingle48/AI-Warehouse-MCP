from storage.db import Database


def test_record_and_get_telemetry(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.record_telemetry(tick=1, robot_id="R1", x=2, y=3, battery=95.5, state="MOVING")

    rows = db.get_telemetry()
    assert len(rows) == 1
    assert rows[0]["robot_id"] == "R1"
    assert rows[0]["battery"] == 95.5


def test_get_telemetry_filters_by_robot(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.record_telemetry(tick=1, robot_id="R1", x=0, y=0, battery=100, state="IDLE")
    db.record_telemetry(tick=1, robot_id="R2", x=0, y=0, battery=100, state="IDLE")

    rows = db.get_telemetry(robot_id="R2")
    assert len(rows) == 1
    assert rows[0]["robot_id"] == "R2"

def test_get_latest_telemetry_per_robot(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.record_telemetry(tick=1, robot_id="R1", x=0, y=0, battery=90, state="MOVING")
    db.record_telemetry(tick=2, robot_id="R1", x=1, y=0, battery=89, state="MOVING")
    db.record_telemetry(tick=2, robot_id="R2", x=5, y=5, battery=70, state="IDLE")

    latest = db.get_latest_telemetry_per_robot()
    assert len(latest) == 2

    r1 = next(r for r in latest if r["robot_id"] == "R1")
    assert r1["x"] == 1

def test_record_and_get_audit_log(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.record_audit("assign_task", {"robot_id": "R1"}, False, "battery too low", None)

    logs = db.get_audit_log()
    assert len(logs) == 1
    assert logs[0]["approved"] == 0
    assert logs[0]["reason"] == "battery too low"