import time

from simulation.task import Task, TaskStatus


def test_task_starts_pending():
    t = Task(task_id="T1", pickup_zone="Pickup", dispatch_zone="Dispatch")
    assert t.status == TaskStatus.PENDING
    assert t.assigned_robot_id is None


def test_task_assignment_flow():
    t = Task(task_id="T1", pickup_zone="Pickup", dispatch_zone="Dispatch")
    t.assign_to("R1")
    assert t.status == TaskStatus.ASSIGNED
    assert t.assigned_robot_id == "R1"

    t.mark_in_progress()
    assert t.status == TaskStatus.IN_PROGRESS

    t.mark_completed()
    assert t.status == TaskStatus.COMPLETED
    assert t.completed_at is not None


def test_task_duration_calculation():
    t = Task(task_id="T1", pickup_zone="Pickup", dispatch_zone="Dispatch")
    time.sleep(0.1)
    t.mark_completed()
    duration = t.duration_seconds()
    assert duration is not None
    assert duration >= 0.1


def test_task_failure():
    t = Task(task_id="T1", pickup_zone="Pickup", dispatch_zone="Dispatch")
    t.assign_to("R1")
    t.mark_failed()
    assert t.status == TaskStatus.FAILED
    assert t.completed_at is not None