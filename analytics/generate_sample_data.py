import random
import sys

from pathlib import Path
from typing import Dict, List
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulation.engine import SimulationEngine
from simulation.robot import Robot
from simulation.task import Task
from simulation.warehouse import Warehouse, build_default_warehouse, zone_distance
from storage.db import Database

DB_PATH = "analytics_sample.db"
NUM_TICKS = 3000
TASK_SPAWN_CHANCE = 0.05


def try_spawn_task(
    engine: SimulationEngine,
    warehouse: Warehouse,
    robot: Robot,
    rng: random.Random,
    zone_names: List[str],
    tick: int,
    task_counter: int,
    task_assigned_tick: Dict[str, int],
    db: Database,
) -> int:
    if not robot.is_available():
        return task_counter
    if rng.random() >= TASK_SPAWN_CHANCE:
        return task_counter

    from_zone, to_zone = rng.sample(zone_names, 2)
    task_counter += 1
    task_id = f"T-{task_counter:04d}"
    task = Task(task_id=task_id, pickup_zone=from_zone, dispatch_zone=to_zone)
    engine.add_task(task)

    try:
        engine.assign_task(task_id, robot.robot_id)
    except ValueError:
        return task_counter

    task_assigned_tick[task_id] = tick
    distance = zone_distance(warehouse, from_zone, to_zone)
    db.record_audit(
        "assign_task",
        {"robot_id": robot.robot_id, "from_zone": from_zone, "to_zone": to_zone},
        True, None,
        {
            "task_id": task_id,
            "tick": tick,
            "battery_at_assignment": robot.battery,
            "distance": distance,
        },
    )
    return task_counter


def main():
    db = Database(DB_PATH)
    warehouse = build_default_warehouse()
    warehouse.add_robot(Robot(robot_id="R1", x=1, y=1))
    warehouse.add_robot(Robot(robot_id="R2", x=6, y=1))
    warehouse.add_robot(Robot(robot_id="R3", x=12, y=6))

    def telemetry_sink(tick_num, robot_obj):
        db.record_telemetry(
            tick_num, robot_obj.robot_id, robot_obj.x, robot_obj.y,
            robot_obj.battery, robot_obj.state.value,
        )

    rng = random.Random(7)
    engine = SimulationEngine(warehouse, rng=rng, failure_probability=0.02, telemetry_sink=telemetry_sink)

    zone_names = list(warehouse.zones.keys())
    task_counter = 0
    task_assigned_tick = {}
    logged_terminal_tasks = set()

    for tick in range(NUM_TICKS):
        if tick % 500 == 0:
            print(f"Progress: tick {tick}/{NUM_TICKS}")

        for robot in warehouse.robots.values():
            task_counter = try_spawn_task(
                engine, warehouse, robot, rng, zone_names, tick, task_counter, task_assigned_tick, db
            )

        engine.tick()

        for robot in warehouse.robots.values():
            if robot.state.value == "FAULT":
                engine.reset_robot(robot.robot_id)

        for task in engine.tasks.values():
            if task.status.value in ("COMPLETED", "FAILED") and task.task_id not in logged_terminal_tasks:
                duration_ticks = tick - task_assigned_tick.get(task.task_id, tick)
                db.record_audit(
                    "task_outcome",
                    {"task_id": task.task_id, "robot_id": task.assigned_robot_id},
                    True, task.status.value, {"duration_ticks": duration_ticks},
                )
                logged_terminal_tasks.add(task.task_id)

    print(f"Done. {task_counter} tasks spawned across {NUM_TICKS} ticks.")
    print(f"Data saved to {DB_PATH}")


if __name__ == "__main__":
    main()