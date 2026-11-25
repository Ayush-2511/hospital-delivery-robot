"""Status enumerations for robots and delivery orders."""

from enum import Enum


class RobotStatus(Enum):
    """Operational states of an Autonomous Mobile Robot (AMR)."""

    IDLE = "IDLE"
    EN_ROUTE_TO_PHARMACY = "EN_ROUTE_TO_PHARMACY"
    WAITING_FOR_CARGO = "WAITING_FOR_CARGO"
    DELIVERING = "DELIVERING"
    OBSTACLE_AVOIDANCE = "OBSTACLE_AVOIDANCE"
    ARRIVED = "ARRIVED"
    UNLATCHED = "UNLATCHED"
    CHARGING = "CHARGING"
    MAINTENANCE = "MAINTENANCE"


class OrderStatus(Enum):
    """Lifecycle states of a medication delivery order."""

    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
