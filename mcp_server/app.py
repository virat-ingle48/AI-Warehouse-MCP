import threading
import uuid
import joblib
import pandas as pd

from simulation.warehouse import zone_distance
from fastmcp import FastMCP
from typing import Optional, cast, Any
from config.settings import DB_PATH
from safety.validator import SafetyValidator
from simulation.engine import SimulationEngine
from simulation.robot import Robot
from simulation.task import Task
from simulation.warehouse import build_default_warehouse
from storage.db import Database


def build_app(db_path: str = DB_PATH):
    db = Database(db_path)

    warehouse = build_default_warehouse()
    warehouse.add_robot(Robot(robot_id="R1", x=1, y=1))
    warehouse.add_robot(Robot(robot_id="R2", x=6, y=1))
    warehouse.add_robot(Robot(robot_id="R3", x=12, y=6))

    def telemetry_sink(tick: int, robot: Robot) -> None:
        db.record_telemetry(tick, robot.robot_id, robot.x, robot.y, robot.battery, robot.state.value)

    engine = SimulationEngine(warehouse, telemetry_sink=telemetry_sink)
    validator = SafetyValidator(warehouse)
    try:
        risk_model = joblib.load("ml_model.joblib")
        risk_model_columns = joblib.load("ml_model_columns.joblib")
        baseline_failure_rate = joblib.load("ml_baseline_rate.joblib")
    except FileNotFoundError:
        risk_model = None
        risk_model_columns = None
        baseline_failure_rate = None
    sim_lock = threading.Lock()

    mcp = FastMCP("ai-warehouse-mcp")

    @mcp.tool
    def get_warehouse_status() -> dict:
        with sim_lock:
            return {
                "tick": engine.tick_count,
                "robots": [
                    {
                        "robot_id": r.robot_id,
                        "position": list(r.position()),
                        "battery": round(r.battery, 1),
                        "state": r.state.value,
                    }
                    for r in warehouse.robots.values()
                ],
            }

    @mcp.tool
    def predict_task_risk(robot_id: str, from_zone: str, to_zone: str) -> dict:
        if risk_model is None or risk_model_columns is None:
            return {"error": "Risk prediction model not available — run analytics/ml_model.ipynb first."}

        model = cast(Any, risk_model)
        model_columns = cast(Any, risk_model_columns)
        baseline_rate = cast(Any, baseline_failure_rate)

        with sim_lock:
            robot = warehouse.get_robot(robot_id)
            if robot is None:
                return {"error": f"Unknown robot_id: {robot_id}"}
            if from_zone not in warehouse.zones or to_zone not in warehouse.zones:
                return {"error": "Unknown zone name"}

            distance = zone_distance(warehouse, from_zone, to_zone)
            battery = robot.battery

        row = {
            "battery_at_assignment": battery,
            "distance": distance,
            f"robot_id_{robot_id}": 1,
            f"from_zone_{from_zone}": 1,
            f"to_zone_{to_zone}": 1,
        }
        input_df = pd.DataFrame([row]).reindex(columns=model_columns, fill_value=0)

        failure_probability = model.predict_proba(input_df)[0][1]

        risk_percent = round(failure_probability * 100, 1)

        comparison = ""
        if baseline_rate is not None:
            baseline_percent: float = round(float(baseline_rate) * 100, 1)
            if risk_percent < baseline_percent - 5:
                comparison = f" This is LOWER than the average task failure rate ({baseline_percent}%) — a relatively safe route."
            elif risk_percent > baseline_percent + 5:
                comparison = f" This is HIGHER than the average task failure rate ({baseline_percent}%) — a relatively risky route."
            else:
                comparison = f" This is close to the average task failure rate ({baseline_percent}%)."

        return {
            "robot_id": robot_id,
            "from_zone": from_zone,
            "to_zone": to_zone,
            "distance": distance,
            "battery": round(battery, 1),
            "predicted_failure_risk_percent": risk_percent,
            "note": (
                "This is a statistical estimate based mainly on route distance — "
                "longer routes accumulate more risk because each movement step has an "
                "independent small chance of failure, regardless of battery level. "
                "This is not a deterministic prediction." + comparison
            ),
        }

    @mcp.tool
    def get_robot_status(robot_id: str) -> dict:
        with sim_lock:
            robot = warehouse.get_robot(robot_id)
            if robot is None:
                return {"error": f"Unknown robot_id: {robot_id}"}
            return {
                "robot_id": robot.robot_id,
                "position": list(robot.position()),
                "battery": round(robot.battery, 1),
                "state": robot.state.value,
                "current_task_id": robot.current_task_id,
            }

    @mcp.tool
    def get_warehouse_layout() -> dict:
        return {
            "zones": [
                {"name": z.name, "type": z.zone_type.value}
                for z in warehouse.zones.values()
            ]
        }

    @mcp.tool
    def assign_task(robot_id: str, from_zone: str, to_zone: str) -> dict:
        with sim_lock:
            validation = validator.validate_assign_task(robot_id, from_zone, to_zone)
            args = {"robot_id": robot_id, "from_zone": from_zone, "to_zone": to_zone}

            if not validation.approved:
                db.record_audit("assign_task", args, False, validation.reason, None)
                return {"success": False, "reason": validation.reason}

            task_id = f"T-{uuid.uuid4().hex[:8]}"
            task = Task(task_id=task_id, pickup_zone=from_zone, dispatch_zone=to_zone)
            engine.add_task(task)
            engine.assign_task(task_id, robot_id)

            result = {"success": True, "task_id": task_id, "assigned_robot": robot_id}
            db.record_audit("assign_task", args, True, None, result)
            return result

    @mcp.tool
    def emergency_stop(robot_id: str) -> dict:
        with sim_lock:
            validation = validator.validate_emergency_stop(robot_id)
            args = {"robot_id": robot_id}

            if not validation.approved:
                db.record_audit("emergency_stop", args, False, validation.reason, None)
                return {"success": False, "reason": validation.reason}

            engine.emergency_stop(robot_id)
            result = {"success": True, "robot_id": robot_id, "state": "EMERGENCY_STOPPED"}
            db.record_audit("emergency_stop", args, True, None, result)
            return result

    @mcp.tool
    def get_task_history() -> dict:
        with sim_lock:
            return {
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "pickup_zone": t.pickup_zone,
                        "dispatch_zone": t.dispatch_zone,
                        "status": t.status.value,
                        "assigned_robot_id": t.assigned_robot_id,
                        "duration_seconds": t.duration_seconds(),
                    }
                    for t in engine.tasks.values()
                ]
            }

    @mcp.tool
    def reset_robot(robot_id: str) -> dict:
        with sim_lock:
            validation = validator.validate_reset_robot(robot_id)
            args = {"robot_id": robot_id}

            if not validation.approved:
                db.record_audit("reset_robot", args, False, validation.reason, None)
                return {"success": False, "reason": validation.reason}

            engine.reset_robot(robot_id)
            result = {"success": True, "robot_id": robot_id, "state": "IDLE"}
            db.record_audit("reset_robot", args, True, None, result)
            return result

    @mcp.tool
    def get_robot_telemetry_history(robot_id: Optional[str] = None, limit: int = 50) -> dict:
        return {"telemetry": db.get_telemetry(robot_id=robot_id, limit=limit)}

    @mcp.tool
    def get_audit_log(limit: int = 50) -> dict:
        return {"audit_log": db.get_audit_log(limit=limit)}

    return mcp, engine, warehouse, db, sim_lock