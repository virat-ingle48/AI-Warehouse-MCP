import random

from simulation.engine import SimulationEngine
from simulation.robot import Robot, RobotState
from simulation.task import Task, TaskStatus
from simulation.warehouse import build_default_warehouse


def make_engine(failure_probability=0.0, seed=42):
    wh = build_default_warehouse()
    return SimulationEngine(wh, rng=random.Random(seed), failure_probability=failure_probability)


def test_robot_moves_one_step_towards_destination():
    engine = make_engine()
    robot = Robot(robot_id="R1", x=0, y=0)
    engine.warehouse.add_robot(robot)
    robot.destination = (5, 0)
    robot.state = RobotState.MOVING

    engine.tick()

    assert robot.position() == (1, 0)
    assert robot.battery < 100.0

def test_emergency_stop_halts_robot_and_fails_task():
    engine = make_engine()
    robot = Robot(robot_id="R1", x=2, y=2, state=RobotState.MOVING)
    engine.warehouse.add_robot(robot)

    task = Task(task_id="T1", pickup_zone="Pickup", dispatch_zone="Dispatch")
    task.assign_to("R1")
    robot.current_task_id = "T1"
    engine.add_task(task)

    engine.emergency_stop("R1")

    assert robot.state == RobotState.EMERGENCY_STOPPED
    assert task.status == TaskStatus.FAILED

def test_reset_robot_returns_to_idle():
    engine = make_engine()
    robot = Robot(
        robot_id="R1", x=1, y=1,
        state=RobotState.EMERGENCY_STOPPED,
        destination=(5, 5), current_task_id="T1",
    )
    engine.warehouse.add_robot(robot)

    engine.reset_robot("R1")

    assert robot.state == RobotState.IDLE
    assert robot.destination is None
    assert robot.current_task_id is None

def test_full_task_lifecycle_completes():
    engine = make_engine()
    robot = Robot(robot_id="R1", x=2, y=2, battery=100)
    engine.warehouse.add_robot(robot)

    task = Task(task_id="T1", pickup_zone="Pickup", dispatch_zone="Dispatch")
    engine.add_task(task)
    engine.assign_task("T1", "R1")

    assert task.status == TaskStatus.ASSIGNED
    assert robot.state == RobotState.MOVING

    for _ in range(60):
        engine.tick()
        if task.status == TaskStatus.COMPLETED:
            break

    assert task.status == TaskStatus.COMPLETED
    assert robot.state == RobotState.IDLE
    assert robot.current_task_id is None


def test_low_battery_idle_robot_starts_charging():
    engine = make_engine()
    robot = Robot(robot_id="R1", x=1, y=1, battery=15, state=RobotState.IDLE)
    engine.warehouse.add_robot(robot)

    engine.tick()

    assert robot.state == RobotState.CHARGING


def test_charging_robot_reaches_full_battery():
    engine = make_engine()
    robot = Robot(robot_id="R1", x=1, y=1, battery=15, state=RobotState.CHARGING)
    engine.warehouse.add_robot(robot)

    for _ in range(30):
        engine.tick()
        if robot.state == RobotState.IDLE:
            break

    assert robot.battery == 100.0
    assert robot.state == RobotState.IDLE


def test_guaranteed_failure_marks_task_failed():
    engine = make_engine(failure_probability=1.0)
    robot = Robot(robot_id="R1", x=0, y=0)
    engine.warehouse.add_robot(robot)
    robot.destination = (5, 0)
    robot.state = RobotState.MOVING
    robot.current_task_id = "T1"

    task = Task(task_id="T1", pickup_zone="Pickup", dispatch_zone="Dispatch")
    task.assign_to("R1")
    engine.add_task(task)

    engine.tick()

    assert robot.state == RobotState.FAULT
    assert task.status == TaskStatus.FAILED