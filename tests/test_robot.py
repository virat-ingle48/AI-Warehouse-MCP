from simulation.robot import Robot, RobotState


def test_robot_starts_idle():
    r = Robot(robot_id="R1", x=0, y=0)
    assert r.state == RobotState.IDLE
    assert r.position() == (0, 0)


def test_robot_availability():
    r = Robot(robot_id="R1", x=0, y=0, battery=50)
    assert r.is_available() is True

    r.state = RobotState.MOVING
    assert r.is_available() is False


def test_low_battery_not_available():
    r = Robot(robot_id="R1", x=0, y=0, battery=15)
    assert r.is_available() is False