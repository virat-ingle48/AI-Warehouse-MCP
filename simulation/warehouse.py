from dataclasses import dataclass, field
from enum import Enum

from config.settings import WAREHOUSE_WIDTH, WAREHOUSE_HEIGHT
from simulation.robot import Robot


class ZoneType(str, Enum):
    STORAGE = "STORAGE"
    PICKUP = "PICKUP"
    PACKAGING = "PACKAGING"
    DISPATCH = "DISPATCH"
    CHARGING = "CHARGING"


@dataclass
class Zone:
    name: str
    zone_type: ZoneType
    x: int
    y: int
    width: int
    height: int

    def contains(self, px: int, py: int) -> bool:
        return self.x <= px < self.x + self.width and self.y <= py < self.y + self.height

    def center(self) -> tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height // 2


@dataclass
class Warehouse:
    width: int = WAREHOUSE_WIDTH
    height: int = WAREHOUSE_HEIGHT
    zones: dict[str, Zone] = field(default_factory=dict)
    robots: dict[str, Robot] = field(default_factory=dict)

    def add_zone(self, zone: Zone) -> None:
        self.zones[zone.name] = zone

    def is_within_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get_zone_at(self, x: int, y: int) -> Zone | None:
        for zone in self.zones.values():
            if zone.contains(x, y):
                return zone
        return None

    def add_robot(self, robot: Robot) -> None:
        if not self.is_within_bounds(robot.x, robot.y):
            raise ValueError(f"Robot {robot.robot_id} position out of bounds")
        self.robots[robot.robot_id] = robot

    def get_robot(self, robot_id: str) -> Robot | None:
        return self.robots.get(robot_id)


def build_default_warehouse() -> Warehouse:
    wh = Warehouse()
    wh.add_zone(Zone("Storage", ZoneType.STORAGE, x=0, y=0, width=4, height=4))
    wh.add_zone(Zone("Pickup", ZoneType.PICKUP, x=5, y=0, width=3, height=3))
    wh.add_zone(Zone("Packaging", ZoneType.PACKAGING, x=9, y=0, width=3, height=3))
    wh.add_zone(Zone("Dispatch", ZoneType.DISPATCH, x=13, y=5, width=2, height=3))
    wh.add_zone(Zone("Charging", ZoneType.CHARGING, x=0, y=13, width=3, height=2))
    return wh

def zone_distance(warehouse: Warehouse, zone_a: str, zone_b: str) -> int:
    ax, ay = warehouse.zones[zone_a].center()
    bx, by = warehouse.zones[zone_b].center()
    return abs(ax - bx) + abs(ay - by)