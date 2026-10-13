import time
from collections import defaultdict, deque
from typing import Deque, Dict

from config.settings import MIN_BATTERY_THRESHOLD, RATE_LIMIT_MAX_COMMANDS, RATE_LIMIT_WINDOW_SECONDS
from safety.rules import ValidationResult
from simulation.robot import RobotState
from simulation.warehouse import Warehouse


class SafetyValidator:
    def __init__(self, warehouse: Warehouse, clock=time.monotonic):
        self.warehouse = warehouse
        self.clock = clock
        self._command_log: Dict[str, Deque[float]] = defaultdict(deque)

    def validate_assign_task(self, robot_id: str, pickup_zone: str, dispatch_zone: str) -> ValidationResult:
        robot = self.warehouse.get_robot(robot_id)
        if robot is None:
            return ValidationResult.reject(f"Unknown robot_id: {robot_id}")

        if pickup_zone not in self.warehouse.zones:
            return ValidationResult.reject(f"Unknown pickup_zone: {pickup_zone}")
        if dispatch_zone not in self.warehouse.zones:
            return ValidationResult.reject(f"Unknown dispatch_zone: {dispatch_zone}")

        if robot.state in (RobotState.FAULT, RobotState.EMERGENCY_STOPPED):
            return ValidationResult.reject(
                f"Robot {robot_id} is in {robot.state} state and cannot accept tasks"
            )

        if robot.state != RobotState.IDLE:
            return ValidationResult.reject(
                f"Robot {robot_id} is not idle (current state: {robot.state})"
            )

        if robot.battery <= MIN_BATTERY_THRESHOLD:
            return ValidationResult.reject(f"Robot {robot_id} battery too low ({robot.battery}%)")

        rate_check = self._check_rate_limit(robot_id)
        if not rate_check.approved:
            return rate_check

        self._record_command(robot_id)
        return ValidationResult.ok()

    def validate_emergency_stop(self, robot_id: str) -> ValidationResult:
        robot = self.warehouse.get_robot(robot_id)
        if robot is None:
            return ValidationResult.reject(f"Unknown robot_id: {robot_id}")

        return ValidationResult.ok()

    def validate_reset_robot(self, robot_id: str) -> ValidationResult:
        robot = self.warehouse.get_robot(robot_id)
        if robot is None:
            return ValidationResult.reject(f"Unknown robot_id: {robot_id}")

        if robot.state not in (RobotState.FAULT, RobotState.EMERGENCY_STOPPED):
            return ValidationResult.reject(
                f"Robot {robot_id} is not in a resettable state (current: {robot.state.value})"
            )
        return ValidationResult.ok()

    def _check_rate_limit(self, robot_id: str) -> ValidationResult:
        now = self.clock()
        window_start = now - RATE_LIMIT_WINDOW_SECONDS
        log = self._command_log[robot_id]

        while log and log[0] < window_start:
            log.popleft()

        if len(log) >= RATE_LIMIT_MAX_COMMANDS:
            return ValidationResult.reject(
                f"Rate limit exceeded for robot {robot_id}: "
                f"max {RATE_LIMIT_MAX_COMMANDS} commands per {RATE_LIMIT_WINDOW_SECONDS}s"
            )
        return ValidationResult.ok()

    def _record_command(self, robot_id: str) -> None:
        self._command_log[robot_id].append(self.clock())