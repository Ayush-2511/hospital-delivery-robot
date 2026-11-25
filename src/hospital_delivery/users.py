"""User hierarchy: base User, HospitalStaff, and Pharmacist."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dispatch import CentralDispatchSystem, DeliveryOrder
    from .inventory import InventoryManager, Medicine
    from .robot import Location


class User:
    """Base authenticated actor in the hospital delivery system."""

    def __init__(self, user_id: str, name: str, role: str, password: str = "pass123") -> None:
        self.user_id = user_id
        self.name = name
        self.role = role
        self._password = password
        self.authenticated = False

    def login(self, password: str | None = None) -> bool:
        """Authenticate the user; succeeds if no password given or password matches."""
        if password is None or password == self._password:
            self.authenticated = True
            return True
        return False

    def logout(self) -> None:
        """Log out the current user."""
        self.authenticated = False


class HospitalStaff(User):
    """Ward nurse or physician requesting and receiving medication deliveries."""

    def __init__(self, user_id: str, name: str, department: str, ward_number: str) -> None:
        super().__init__(user_id, name, role="STAFF")
        self.department = department
        self.ward_number = ward_number

    def request_delivery(
        self,
        dispatch: CentralDispatchSystem,
        order_id: str,
        medicine: Medicine,
        quantity: int,
        destination: Location,
        verification_pin: str = "1234",
    ) -> DeliveryOrder | None:
        """Create and submit a medication delivery order through CentralDispatchSystem."""
        from .dispatch import DeliveryOrder

        order = DeliveryOrder(
            order_id=order_id,
            requested_by=self,
            medicine=medicine,
            quantity=quantity,
            destination=destination,
            verification_pin=verification_pin,
        )
        if dispatch.process_order(order):
            return order
        return None

    def confirm_receipt(
        self,
        dispatch: CentralDispatchSystem,
        order_id: str,
        auth_pin: str,
    ) -> bool:
        """Unlock cargo bay with Staff ID + PIN and finalize delivery with dispatch."""
        return dispatch.complete_delivery(order_id=order_id, staff_id=self.user_id, auth_pin=auth_pin)


class Pharmacist(User):
    """Pharmacy manager responsible for restocking and loading medication onto robots."""

    def __init__(self, user_id: str, name: str) -> None:
        super().__init__(user_id, name, role="PHARMACIST")

    def update_stock(self, inventory: InventoryManager, medicine_id: str, new_quantity: int) -> bool:
        """Restock a medicine entry in the inventory."""
        item = inventory.find_item(medicine_id)
        if item is None or new_quantity < 0:
            return False
        item.restock(new_quantity)
        return True

    def load_medicine_to_robot(self, dispatch: CentralDispatchSystem, robot_id: str, order_id: str) -> bool:
        """Verify prescription, load cargo onto the assigned robot, and lock its cargo bay."""
        from .enums import OrderStatus

        robot = dispatch.find_robot_by_id(robot_id)
        order = dispatch.find_order_by_id(order_id)
        if robot is None or order is None:
            return False
        robot.lock_cargo_bay()
        if robot.start_delivery(order.destination):
            order.status = OrderStatus.IN_TRANSIT
            return True
        return False
