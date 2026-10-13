from safety.validator import SafetyValidator
from simulation.robot import Robot, RobotState
from simulation.warehouse import build_default_warehouse


def make_validator(clock=None):
    wh = build_default_warehouse()
    return wh, SafetyValidator(wh, clock=clock or (lambda: 0.0))


def test_reject_unknown_robot():
    wh, validator = make_validator()
    result = validator.validate_assign_task("R99", "Pickup", "Dispatch")
    assert result.approved is False
    assert "Unknown robot_id" in result.reason


def test_reject_unknown_zone():
    wh, validator = make_validator()
    wh.add_robot(Robot(robot_id="R1", x=1, y=1))
    result = validator.validate_assign_task("R1", "NotAZone", "Dispatch")
    assert result.approved is False
    assert "Unknown pickup_zone" in result.reason


def test_reject_fault_state_robot():
    wh, validator = make_validator()
    wh.add_robot(Robot(robot_id="R1", x=1, y=1, state=RobotState.FAULT))
    result = validator.validate_assign_task("R1", "Pickup", "Dispatch")
    assert result.approved is False
    assert "FAULT" in result.reason


def test_reset_rejected_for_idle_robot():
    wh, validator = make_validator()
    wh.add_robot(Robot(robot_id="R1", x=1, y=1, state=RobotState.IDLE))
    result = validator.validate_reset_robot("R1")
    assert result.approved is False

def test_reset_approved_for_emergency_stopped_robot():
    wh, validator = make_validator()
    wh.add_robot(Robot(robot_id="R1", x=1, y=1, state=RobotState.EMERGENCY_STOPPED))
    result = validator.validate_reset_robot("R1")
    assert result.approved is True

def test_reject_non_idle_moving_robot():
    wh, validator = make_validator()
    wh.add_robot(Robot(robot_id="R1", x=1, y=1, state=RobotState.MOVING, battery=100))
    result = validator.validate_assign_task("R1", "Pickup", "Dispatch")
    assert result.approved is False
    assert "not idle" in result.reason.lower()


def test_reject_low_battery_robot():
    wh, validator = make_validator()
    wh.add_robot(Robot(robot_id="R1", x=1, y=1, battery=10))
    result = validator.validate_assign_task("R1", "Pickup", "Dispatch")
    assert result.approved is False
    assert "battery" in result.reason.lower()


def test_approve_valid_assign_task():
    wh, validator = make_validator()
    wh.add_robot(Robot(robot_id="R1", x=1, y=1, battery=100))
    result = validator.validate_assign_task("R1", "Pickup", "Dispatch")
    assert result.approved is True


def test_rate_limit_blocks_after_max_commands():
    fake_time = [0.0]
    wh, validator = make_validator(clock=lambda: fake_time[0])
    wh.add_robot(Robot(robot_id="R1", x=1, y=1, battery=100))

    for _ in range(3):  # RATE_LIMIT_MAX_COMMANDS = 3
        result = validator.validate_assign_task("R1", "Pickup", "Dispatch")
        assert result.approved is True
        fake_time[0] += 1.0

    result = validator.validate_assign_task("R1", "Pickup", "Dispatch")
    assert result.approved is False
    assert "Rate limit" in result.reason


def test_emergency_stop_always_approved_even_in_fault_state():
    wh, validator = make_validator()
    wh.add_robot(Robot(robot_id="R1", x=1, y=1, state=RobotState.FAULT))
    result = validator.validate_emergency_stop("R1")
    assert result.approved is True