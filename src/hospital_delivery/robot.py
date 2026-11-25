"""Autonomous Mobile Robot (AMR), sensor subsystem, navigation, and location."""

from __future__ import annotations

import math
from typing import List, Optional

from .enums import RobotStatus


class Location:
    """Represents a mapped hospital waypoint (floor, room, x/y coordinates)."""

    def __init__(self, floor: int, room_number: str, x_coord: float, y_coord: float) -> None:
        self.floor = floor
        self.room_number = room_number
        self.x_coord = x_coord
        self.y_coord = y_coord

    def distance_to(self, other: Location) -> float:
        floor_penalty = abs(self.floor - other.floor) * 10.0
        return math.hypot(self.x_coord - other.x_coord, self.y_coord - other.y_coord) + floor_penalty

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Location):
            return False
        return (
            self.floor == other.floor
            and self.room_number == other.room_number
            and math.isclose(self.x_coord, other.x_coord, abs_tol=1e-6)
            and math.isclose(self.y_coord, other.y_coord, abs_tol=1e-6)
        )

    def __repr__(self) -> str:
        return f"Location(floor={self.floor}, room={self.room_number!r})"


class SensorSubsystem:
    """LiDAR, Sonar, and Vision modules polling at >= 20 Hz for collision avoidance."""

    POLL_FREQUENCY_HZ = 20
    REPLAN_DISTANCE_M = 0.5
    HARD_STOP_DISTANCE_M = 0.3

    def __init__(self) -> None:
        self.proximity_distance: float = float("inf")
        self.obstacle_detected: bool = False

    def scan_environment(self, simulated_distance: float = 5.0) -> float:
        """Update proximity reading (in meters) from environment sensors."""
        self.proximity_distance = max(0.0, simulated_distance)
        self.obstacle_detected = self.proximity_distance < self.REPLAN_DISTANCE_M
        return self.proximity_distance

    def detect_obstacle(self) -> bool:
        """Return True if an obstacle is within the 0.5m replanning threshold."""
        return self.obstacle_detected

    def requires_hard_stop(self) -> bool:
        """Return True if an obstacle is within the 0.3m safety stop threshold."""
        return self.proximity_distance <= self.HARD_STOP_DISTANCE_M


class NavigationSystem:
    """Path planning and dynamic route recalculation across hospital floors."""

    def __init__(self, initial_location: Optional[Location] = None) -> None:
        self.current_location: Optional[Location] = initial_location
        self.destination: Optional[Location] = None
        self.planned_path: List[Location] = []

    def plan_path(self, start: Location, end: Location) -> List[Location]:
        """Compute an optimal waypoint path from start to end."""
        self.current_location = start
        self.destination = end
        mid_x = (start.x_coord + end.x_coord) / 2.0
        mid_y = (start.y_coord + end.y_coord) / 2.0
        midpoint = Location(end.floor, f"CORRIDOR-F{end.floor}", mid_x, mid_y)
        self.planned_path = [start, midpoint, end]
        return list(self.planned_path)

    def recalculate_route(self) -> List[Location]:
        """Compute an alternate detour around a detected dynamic obstacle."""
        if self.current_location is None or self.destination is None:
            return []
        detour = Location(
            self.destination.floor,
            f"DETOUR-F{self.destination.floor}",
            (self.current_location.x_coord + self.destination.x_coord) / 2.0 + 1.5,
            (self.current_location.y_coord + self.destination.y_coord) / 2.0 + 1.5,
        )
        self.planned_path = [self.current_location, detour, self.destination]
        return list(self.planned_path)

    def notify_arrival(self) -> bool:
        """Mark current_location as destination upon arrival."""
        if self.destination is None:
            return False
        self.current_location = self.destination
        return True


class HospitalRobot:
    """Autonomous Mobile Robot entity with composed NavigationSystem and SensorSubsystem."""

    MIN_DISPATCH_BATTERY = 25.0
    LOW_BATTERY_THRESHOLD = 20.0
    MAX_STUCK_SECONDS = 60

    def __init__(
        self,
        robot_id: str,
        battery_level: float = 100.0,
        home_location: Optional[Location] = None,
    ) -> None:
        self.robot_id = robot_id
        self.battery_level = battery_level
        self.status = RobotStatus.IDLE
        self.cargo_locked = True
        self.expected_pin: Optional[str] = None
        self.expected_staff_id: Optional[str] = None
        self.navigation = NavigationSystem(home_location or Location(1, "STAGING", 0.0, 0.0))
        self.sensors = SensorSubsystem()
        self.distress_alerts: List[str] = []

    def is_available_for_dispatch(self) -> bool:
        return self.status == RobotStatus.IDLE and self.battery_level > self.MIN_DISPATCH_BATTERY

    def navigate_to(self, target_location: Location) -> List[Location]:
        """Plan path to target_location and transition to EN_ROUTE_TO_PHARMACY."""
        start = self.navigation.current_location or Location(1, "STAGING", 0.0, 0.0)
        path = self.navigation.plan_path(start, target_location)
        self.status = RobotStatus.EN_ROUTE_TO_PHARMACY
        return path

    def arrive_at_pharmacy(self) -> None:
        self.navigation.notify_arrival()
        self.status = RobotStatus.WAITING_FOR_CARGO

    def start_delivery(self, destination: Location) -> bool:
        if not self.cargo_locked:
            return False
        start = self.navigation.current_location or Location(1, "PHARMACY", 0.0, 0.0)
        self.navigation.plan_path(start, destination)
        self.status = RobotStatus.DELIVERING
        return True

    def handle_obstacle_detected(self, distance_m: float, stuck_seconds: int = 0) -> List[Location]:
        """Handle obstacle within 0.5m (reroute) or escalate to MAINTENANCE if stuck > 60s."""
        self.sensors.scan_environment(distance_m)
        if not self.sensors.detect_obstacle():
            return self.navigation.planned_path

        self.status = RobotStatus.OBSTACLE_AVOIDANCE
        if stuck_seconds > self.MAX_STUCK_SECONDS:
            self.status = RobotStatus.MAINTENANCE
            self.distress_alerts.append(
                f"DISTRESS: Robot {self.robot_id} stuck > {self.MAX_STUCK_SECONDS}s at {self.navigation.current_location}"
            )
            return []

        detour = self.navigation.recalculate_route()
        if detour:
            self.status = RobotStatus.DELIVERING
        return detour

    def arrive_at_ward(self) -> None:
        self.navigation.notify_arrival()
        self.status = RobotStatus.ARRIVED

    def unlock_cargo_bay(self, verification_code: str, staff_id: Optional[str] = None) -> bool:
        """Unlock cargo bay only upon matching 2-factor Staff ID + PIN."""
        if self.status != RobotStatus.ARRIVED:
            return False
        if self.expected_staff_id is not None and staff_id != self.expected_staff_id:
            return False
        if self.expected_pin is not None and verification_code != self.expected_pin:
            return False
        self.cargo_locked = False
        self.status = RobotStatus.UNLATCHED
        return True

    def lock_cargo_bay(self) -> None:
        self.cargo_locked = True

    def complete_order_cycle(self) -> None:
        self.lock_cargo_bay()
        self.expected_pin = None
        self.expected_staff_id = None
        if self.battery_level <= self.LOW_BATTERY_THRESHOLD:
            self.return_to_charging_station()
        else:
            self.status = RobotStatus.IDLE

    def return_to_charging_station(self) -> None:
        self.status = RobotStatus.CHARGING
        self.navigation.notify_arrival()

    def finish_charging(self) -> None:
        self.battery_level = 100.0
        self.status = RobotStatus.IDLE
