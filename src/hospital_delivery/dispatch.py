"""DeliveryOrder and CentralDispatchSystem coordination logic."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from .enums import OrderStatus, RobotStatus
from .inventory import InventoryManager, Medicine
from .robot import HospitalRobot, Location
from .users import HospitalStaff


class DeliveryOrder:
    """Represents a medication delivery request from ward staff."""

    def __init__(
        self,
        order_id: str,
        requested_by: HospitalStaff,
        medicine: Medicine,
        quantity: int,
        destination: Location,
        verification_pin: str = "1234",
    ) -> None:
        self.order_id = order_id
        self.requested_by = requested_by
        self.medicine = medicine
        self.quantity = quantity
        self.destination = destination
        self.status = OrderStatus.PENDING
        self.verification_pin = verification_pin
        self.assigned_robot_id: Optional[str] = None
        self.timestamp = datetime.now()


class CentralDispatchSystem:
    """Coordinates orders, real-time inventory, and the HospitalRobot fleet."""

    def __init__(self, pharmacy_location: Optional[Location] = None) -> None:
        self.active_robots: List[HospitalRobot] = []
        self.orders: List[DeliveryOrder] = []
        self.inventory = InventoryManager()
        self.pharmacy_location = pharmacy_location or Location(1, "CENTRAL-PHARMACY", 0.0, 0.0)
        self.notifications: List[str] = []

    def register_robot(self, robot: HospitalRobot) -> None:
        self.active_robots.append(robot)

    def find_robot_by_id(self, robot_id: str) -> Optional[HospitalRobot]:
        for robot in self.active_robots:
            if robot.robot_id == robot_id:
                return robot
        return None

    def find_order_by_id(self, order_id: str) -> Optional[DeliveryOrder]:
        for order in self.orders:
            if order.order_id == order_id:
                return order
        return None

    def process_order(self, order: DeliveryOrder) -> bool:
        """Validate stock, reserve inventory, queue order, and dispatch an idle robot."""
        if not self.inventory.reserve_items(order.medicine.medicine_id, order.quantity):
            order.status = OrderStatus.CANCELLED
            self.orders.append(order)
            return False

        self.orders.append(order)
        robot = self.find_available_robot()
        if robot is None:
            return False

        self.assign_robot_to_order(robot, order)
        return True

    def find_available_robot(self) -> Optional[HospitalRobot]:
        """Select the available IDLE robot (>25% battery) closest to the pharmacy."""
        candidates = [r for r in self.active_robots if r.is_available_for_dispatch()]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda r: (
                r.navigation.current_location.distance_to(self.pharmacy_location)
                if r.navigation.current_location
                else 0.0
            ),
        )

    def assign_robot_to_order(self, robot: HospitalRobot, order: DeliveryOrder) -> None:
        """Bind robot to order, configure 2-factor credentials, and route to pharmacy."""
        order.assigned_robot_id = robot.robot_id
        order.status = OrderStatus.ASSIGNED
        robot.expected_pin = order.verification_pin
        robot.expected_staff_id = order.requested_by.user_id
        robot.navigate_to(self.pharmacy_location)

    def notify_staff_arrival(self, staff: HospitalStaff, order_id: str) -> None:
        self.notifications.append(
            f"ARRIVAL: Order {order_id} arrived at {staff.ward_number} for {staff.name}. Enter PIN to unlock."
        )

    def complete_delivery(self, order_id: str, staff_id: str, auth_pin: str) -> bool:
        """Verify 2FA unlock, deduct inventory stock, and close order."""
        order = self.find_order_by_id(order_id)
        if order is None or order.assigned_robot_id is None:
            return False
        robot = self.find_robot_by_id(order.assigned_robot_id)
        if robot is None:
            return False

        if not robot.unlock_cargo_bay(verification_code=auth_pin, staff_id=staff_id):
            return False

        item = self.inventory.find_item(order.medicine.medicine_id)
        if item is None:
            return False
        item.deduct_stock(order.quantity)
        order.status = OrderStatus.DELIVERED
        robot.complete_order_cycle()
        return True
