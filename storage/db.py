import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class Database:
    def __init__(self, db_path: str = "warehouse.db"):
        self.db_path = db_path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(SCHEMA_PATH.read_text())
            conn.commit()
        finally:
            conn.close()

    def record_telemetry(self, tick: int, robot_id: str, x: int, y: int, battery: float, state: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO telemetry (tick, robot_id, x, y, battery, state, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (tick, robot_id, x, y, battery, state, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def record_audit(self, tool_name: str, arguments: dict, approved: bool,
                      reason: Optional[str], result: Optional[dict]) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO audit_log (tool_name, arguments, approved, reason, result, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    tool_name,
                    json.dumps(arguments),
                    1 if approved else 0,
                    reason,
                    json.dumps(result) if result is not None else None,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_telemetry(self, robot_id: Optional[str] = None, limit: int = 100) -> list[dict]:
        conn = self._connect()
        try:
            if robot_id:
                rows = conn.execute(
                    "SELECT * FROM telemetry WHERE robot_id = ? ORDER BY id DESC LIMIT ?",
                    (robot_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM telemetry ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_latest_telemetry_per_robot(self) -> list[dict]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT t.* FROM telemetry t
                INNER JOIN (
                    SELECT robot_id, MAX(id) AS max_id
                    FROM telemetry
                    GROUP BY robot_id
                ) latest ON t.robot_id = latest.robot_id AND t.id = latest.max_id
                """
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_audit_log(self, limit: int = 100) -> list[dict]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()