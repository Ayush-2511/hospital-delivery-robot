"""Unit and integration tests covering FR-01 through FR-08 and NFR safety guards."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hospital_delivery import (
    CentralDispatchSystem,
    HospitalRobot,
    HospitalStaff,
    InventoryItem,
    Location,
    Medicine,
    OrderStatus,
    Pharmacist,
    RobotStatus,
)


class TestHospitalDeliverySystem(unittest.TestCase):
    def setUp(self) -> None:
        self.pharmacy = Location(1, "PHARMACY", 0.0, 0.0)
        self.ward = Location(2, "WARD-201", 20.0, 10.0)
        self.dispatch = CentralDispatchSystem(pharmacy_location=self.pharmacy)
        self.med = Medicine("MED-01", "Insulin", "Endocrine", required_temp=4.0)
        self.dispatch.inventory.add_item(InventoryItem(self.med, quantity=10, threshold_limit=5))
        self.robot = HospitalRobot("AMR-01", battery_level=80.0, home_location=Location(1, "DOCK", 1.0, 1.0))
        self.dispatch.register_robot(self.robot)
        self.staff = HospitalStaff("STF-01", "Nurse Rao", "General", "WARD-201")
        self.pharmacist = Pharmacist("PHM-01", "Pharmacist Ali")

    def test_fr01_authentication(self) -> None:
        self.assertTrue(self.staff.login("pass123"))
        self.assertTrue(self.staff.authenticated)
        self.staff.logout()
        self.assertFalse(self.staff.authenticated)
        self.assertFalse(self.staff.login("wrong"))

    def test_fr02_to_fr08_full_delivery_cycle(self) -> None:
        order = self.staff.request_delivery(
            self.dispatch, "ORD-01", self.med, 3, self.ward, verification_pin="9988"
        )
        self.assertIsNotNone(order)
        assert order is not None
        self.assertEqual(order.status, OrderStatus.ASSIGNED)
        self.assertEqual(self.robot.status, RobotStatus.EN_ROUTE_TO_PHARMACY)

        self.robot.arrive_at_pharmacy()
        self.assertEqual(self.robot.status, RobotStatus.WAITING_FOR_CARGO)

        self.assertTrue(self.pharmacist.load_medicine_to_robot(self.dispatch, "AMR-01", "ORD-01"))
        self.assertEqual(self.robot.status, RobotStatus.DELIVERING)
        self.assertTrue(self.robot.cargo_locked)

        # Obstacle within 0.5m triggers rerouting and resumes DELIVERING
        detour = self.robot.handle_obstacle_detected(distance_m=0.45)
        self.assertEqual(len(detour), 3)
        self.assertEqual(self.robot.status, RobotStatus.DELIVERING)

        self.robot.arrive_at_ward()
        self.assertEqual(self.robot.status, RobotStatus.ARRIVED)

        # Wrong PIN rejected
        self.assertFalse(self.staff.confirm_receipt(self.dispatch, "ORD-01", "0000"))
        # Correct PIN unlocks, deducts stock, closes order
        self.assertTrue(self.staff.confirm_receipt(self.dispatch, "ORD-01", "9988"))
        self.assertEqual(order.status, OrderStatus.DELIVERED)
        self.assertEqual(self.dispatch.inventory.find_item("MED-01").quantity, 7)
        self.assertEqual(self.robot.status, RobotStatus.IDLE)

    def test_fr04_low_stock_alert_and_out_of_stock(self) -> None:
        # Ordering 7 leaves 3 (< threshold 5) -> triggers low stock alert
        order = self.staff.request_delivery(self.dispatch, "ORD-02", self.med, 7, self.ward)
        self.assertIsNotNone(order)
        self.assertEqual(len(self.dispatch.inventory.alerts), 1)

        # Ordering 5 more when only 3 available -> fails and cancels
        order2 = self.staff.request_delivery(self.dispatch, "ORD-03", self.med, 5, self.ward)
        self.assertIsNone(order2)

    def test_battery_guard_and_fail_safe_maintenance(self) -> None:
        # Robot with <=25% battery cannot be dispatched
        self.robot.battery_level = 20.0
        self.assertIsNone(self.dispatch.find_available_robot())

        # Stuck > 60s escalates to MAINTENANCE with distress alert
        self.robot.battery_level = 90.0
        self.robot.status = RobotStatus.DELIVERING
        self.robot.handle_obstacle_detected(distance_m=0.25, stuck_seconds=65)
        self.assertTrue(self.robot.sensors.requires_hard_stop())
        self.assertEqual(self.robot.status, RobotStatus.MAINTENANCE)
        self.assertEqual(len(self.robot.distress_alerts), 1)


if __name__ == "__main__":
    unittest.main()
