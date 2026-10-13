from dataclasses import dataclass
from enum import Enum

from config.settings import MIN_BATTERY_THRESHOLD


class RobotState(str, Enum):
    IDLE = "IDLE"
    MOVING = "MOVING"
    DELIVERING = "DELIVERING"
    CHARGING = "CHARGING"
    FAULT = "FAULT"
    EMERGENCY_STOPPED = "EMERGENCY_STOPPED"


@dataclass
class Robot:
    robot_id: str
    x: int
    y: int
    battery: float = 100.0
    state: RobotState = RobotState.IDLE
    destination: tuple[int, int] | None = None
    current_task_id: str | None = None
    speed: int = 1

    def position(self) -> tuple[int, int]:
        return self.x, self.y

    def is_available(self) -> bool:
        return self.state == RobotState.IDLE and self.battery > MIN_BATTERY_THRESHOLD