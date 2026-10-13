from simulation.robot import Robot
from simulation.warehouse import Zone, ZoneType, build_default_warehouse


def test_zone_contains_point():
    z = Zone("Storage", ZoneType.STORAGE, x=0, y=0, width=4, height=4)
    assert z.contains(2, 2) is True
    assert z.contains(4, 4) is False


def test_default_warehouse_has_five_zones():
    wh = build_default_warehouse()
    assert len(wh.zones) == 5
    assert "Storage" in wh.zones
    assert "Charging" in wh.zones


def test_get_zone_at_position():
    wh = build_default_warehouse()
    zone = wh.get_zone_at(1, 1)
    assert zone is not None
    assert zone.name == "Storage"

    empty = wh.get_zone_at(7, 10)
    assert empty is None


def test_add_robot_within_bounds():
    wh = build_default_warehouse()
    r = Robot(robot_id="R1", x=2, y=2)
    wh.add_robot(r)
    assert wh.get_robot("R1") is r


def test_add_robot_out_of_bounds_raises_error():
    wh = build_default_warehouse()
    r = Robot(robot_id="R1", x=99, y=99)
    try:
        wh.add_robot(r)
        assert False, "Expected ValueError but nothing raised"
    except ValueError:
        pass