"""End-to-end CLI simulation of the Autonomous Hospital Delivery Robot & Inventory System."""

from pathlib import Path
import sys

# Ensure src/ is on sys.path when running directly via `python main.py`
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from hospital_delivery import (
    CentralDispatchSystem,
    HospitalRobot,
    HospitalStaff,
    InventoryItem,
    Location,
    Medicine,
    Pharmacist,
)


def run_simulation() -> None:
    print("=== Autonomous Hospital Delivery Robot & Inventory System ===\n")

    # 1. Initialize locations, dispatch, inventory, and fleet
    pharmacy_loc = Location(floor=1, room_number="CENTRAL-PHARMACY", x_coord=0.0, y_coord=0.0)
    icu_ward = Location(floor=2, room_number="ICU-204", x_coord=25.0, y_coord=12.0)

    dispatch = CentralDispatchSystem(pharmacy_location=pharmacy_loc)
    amoxicillin = Medicine("MED-101", "Amoxicillin 500mg", "Antibiotic", required_temp=20.0)
    dispatch.inventory.add_item(InventoryItem(amoxicillin, quantity=12, threshold_limit=5))

    robot = HospitalRobot("AMR-01", battery_level=82.0, home_location=Location(1, "STAGING", 2.0, 1.0))
    dispatch.register_robot(robot)

    # 2. Authenticate actors (FR-01)
    nurse = HospitalStaff("STF-07", "Nurse Priya", department="ICU", ward_number="ICU-204")
    pharmacist = Pharmacist("PHM-02", "Dr. Mehta")
    assert nurse.login() and pharmacist.login()
    print(f"[Auth] Logged in: {nurse.name} ({nurse.role}), {pharmacist.name} ({pharmacist.role})")

    # 3. Ward staff places delivery request (FR-02, FR-03, FR-05)
    order = nurse.request_delivery(
        dispatch=dispatch,
        order_id="ORD-1001",
        medicine=amoxicillin,
        quantity=4,
        destination=icu_ward,
        verification_pin="4821",
    )
    assert order is not None
    print(f"[Dispatch] Order {order.order_id} created -> Assigned {robot.robot_id} ({robot.status.value})")

    # 4. Robot arrives at pharmacy & pharmacist loads cargo (FR-08)
    robot.arrive_at_pharmacy()
    print(f"[Robot] {robot.robot_id} reached pharmacy -> {robot.status.value}")
    pharmacist.load_medicine_to_robot(dispatch, robot.robot_id, order.order_id)
    print(f"[Pharmacy] Cargo loaded & locked -> {robot.status.value}")

    # 5. Dynamic obstacle detection & rerouting during transit (FR-06, FR-07)
    detour = robot.handle_obstacle_detected(distance_m=0.42)
    print(f"[Sensors] Obstacle at 0.42m (<0.5m) -> Rerouted via {detour[1]} -> {robot.status.value}")

    # 6. Arrival at destination ward & 2FA PIN unlock (FR-08)
    robot.arrive_at_ward()
    dispatch.notify_staff_arrival(nurse, order.order_id)
    print(f"[Notify] {dispatch.notifications[-1]}")

    wrong_unlock = nurse.confirm_receipt(dispatch, order.order_id, auth_pin="0000")
    print(f"[Security] Unlock attempt with wrong PIN '0000': {wrong_unlock}")

    verified = nurse.confirm_receipt(dispatch, order.order_id, auth_pin="4821")
    remaining = dispatch.inventory.find_item("MED-101").quantity
    print(f"[Delivery] 2FA PIN '4821' verified={verified} -> Order={order.status.value}, Stock left={remaining}, Robot={robot.status.value}")


if __name__ == "__main__":
    run_simulation()
