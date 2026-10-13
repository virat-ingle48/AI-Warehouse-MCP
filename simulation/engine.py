import random
from typing import Dict, Optional,Callable

from config.settings import MIN_BATTERY_THRESHOLD, BATTERY_DRAIN_PER_MOVE, CHARGE_RATE_PER_TICK, FAILURE_PROBABILITY
from simulation.robot import Robot, RobotState
from simulation.task import Task, TaskStatus
from simulation.warehouse import Warehouse


class SimulationEngine:
    def __init__(
        self,
        warehouse: Warehouse,
        rng: Optional[random.Random] = None,
        failure_probability: float = FAILURE_PROBABILITY,
        telemetry_sink: Optional[Callable[[int, "Robot"], None]] = None,
    ):
        self.warehouse = warehouse
        self.tasks: Dict[str, Task] = {}
        self.tick_count = 0
        self.rng = rng or random.Random()
        self.failure_probability = failure_probability
        self.telemetry_sink = telemetry_sink

    def add_task(self, task: Task) -> None:
        self.tasks[task.task_id] = task

    def assign_task(self, task_id: str, robot_id: str) -> None:
        task = self.tasks[task_id]
        robot = self.warehouse.get_robot(robot_id)
        if robot is None:
            raise ValueError(f"Unknown robot: {robot_id}")
        if not robot.is_available():
            raise ValueError(f"Robot {robot_id} is not available")

        pickup_zone = self.warehouse.zones[task.pickup_zone]
        robot.destination = pickup_zone.center()
        robot.current_task_id = task.task_id
        robot.state = RobotState.MOVING
        task.assign_to(robot_id)

    def emergency_stop(self, robot_id: str) -> None:
        robot = self.warehouse.get_robot(robot_id)
        if robot is None:
            raise ValueError(f"Unknown robot: {robot_id}")

        robot.state = RobotState.EMERGENCY_STOPPED
        if robot.current_task_id:
            task = self.tasks.get(robot.current_task_id)
            if task:
                task.mark_failed()

    def tick(self) -> None:
        self.tick_count += 1
        for robot in self.warehouse.robots.values():
            self._update_robot(robot)
            if self.telemetry_sink:
                self.telemetry_sink(self.tick_count, robot)

    def _update_robot(self, robot: Robot) -> None:
        if robot.state in (RobotState.EMERGENCY_STOPPED, RobotState.FAULT):
            return

        if robot.state == RobotState.CHARGING:
            self._charge(robot)
        elif robot.state == RobotState.MOVING:
            self._move_towards_destination(robot)
        elif robot.state == RobotState.DELIVERING:
            self._handle_pickup_complete(robot)
        elif robot.state == RobotState.IDLE:
            if robot.battery <= MIN_BATTERY_THRESHOLD:
                robot.state = RobotState.CHARGING

    def _move_towards_destination(self, robot: Robot) -> None:
        if robot.destination is None:
            robot.state = RobotState.IDLE
            return

        if self.rng.random() < self.failure_probability:
            robot.state = RobotState.FAULT
            if robot.current_task_id:
                self.tasks[robot.current_task_id].mark_failed()
            return

        dx = robot.destination[0] - robot.x
        dy = robot.destination[1] - robot.y
        if dx != 0:
            robot.x += 1 if dx > 0 else -1
        elif dy != 0:
            robot.y += 1 if dy > 0 else -1

        robot.battery = max(0.0, robot.battery - BATTERY_DRAIN_PER_MOVE)

        if robot.position() == robot.destination:
            self._arrive(robot)

    def reset_robot(self, robot_id: str) -> None:
        robot = self.warehouse.get_robot(robot_id)
        if robot is None:
            raise ValueError(f"Unknown robot: {robot_id}")
        robot.state = RobotState.IDLE
        robot.destination = None
        robot.current_task_id = None

    def _arrive(self, robot: Robot) -> None:
        task = self.tasks.get(robot.current_task_id) if robot.current_task_id else None
        if task is None:
            robot.state = RobotState.IDLE
            robot.destination = None
            return

        if task.status == TaskStatus.ASSIGNED:
            task.mark_in_progress()
            robot.state = RobotState.DELIVERING  # pickup zone pe loading
        elif task.status == TaskStatus.IN_PROGRESS:
            task.mark_completed()
            robot.state = RobotState.IDLE
            robot.current_task_id = None
            robot.destination = None

    def _handle_pickup_complete(self, robot: Robot) -> None:
        if robot.current_task_id is None:
            robot.state = RobotState.IDLE
            return
        task = self.tasks[robot.current_task_id]
        dispatch_zone = self.warehouse.zones[task.dispatch_zone]
        robot.destination = dispatch_zone.center()
        robot.state = RobotState.MOVING

    @staticmethod
    def _charge(robot: Robot) -> None:
        robot.battery = min(100.0, robot.battery + CHARGE_RATE_PER_TICK)
        if robot.battery >= 100.0:
            robot.state = RobotState.IDLE