from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class Task:
    task_id: str
    pickup_zone: str
    dispatch_zone: str
    status: TaskStatus = TaskStatus.PENDING
    assigned_robot_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def assign_to(self, robot_id: str) -> None:
        self.assigned_robot_id = robot_id
        self.status = TaskStatus.ASSIGNED

    def mark_in_progress(self) -> None:
        self.status = TaskStatus.IN_PROGRESS

    def mark_completed(self) -> None:
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()

    def mark_failed(self) -> None:
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()

    def duration_seconds(self) -> Optional[float]:
        if self.completed_at is None:
            return None
        return (self.completed_at - self.created_at).total_seconds()