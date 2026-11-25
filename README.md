# Autonomous Hospital Delivery Robot & Inventory Tracking System

Software Engineering (CS/SE) academic project implementing an **Autonomous Mobile Robot (AMR)** dispatch and real-time medicine inventory management system.

## Repository Contents

```text
hospital-delivery-robot/
├── SRS.pdf                         # IEEE-style Software Requirements Specification + UML Diagrams
├── main.py                         # End-to-end CLI simulation of the 18-step delivery cycle
├── src/
│   └── hospital_delivery/
│       ├── __init__.py
│       ├── enums.py                # RobotStatus and OrderStatus enumerations
│       ├── users.py                # User, HospitalStaff, and Pharmacist classes
│       ├── inventory.py            # Medicine, InventoryItem, and InventoryManager
│       ├── robot.py                # Location, SensorSubsystem, NavigationSystem, HospitalRobot
│       └── dispatch.py             # DeliveryOrder and CentralDispatchSystem
└── tests/
    └── test_delivery_system.py     # Unit & integration tests for FR-01..FR-08 and NFR safety guards
```

## Prerequisites

- **Python 3.10+** (uses only the Python standard library — no external packages required).

## How to Use

### 1. Run the End-to-End Simulation
From the repository root:

```bash
python main.py
```

This simulates:
1. Staff and Pharmacist authentication (`FR-01`).
2. Medication order creation and real-time inventory reservation (`FR-02`, `FR-03`).
3. Nearest-robot dispatch with battery guard (`> 25%`) (`FR-05`).
4. Pharmacy cargo loading and locking (`FR-08`).
5. Dynamic obstacle detection (`< 0.5 m`) and route recalculation (`FR-06`, `FR-07`).
6. Ward arrival, 2-factor verification (`Staff ID + PIN`), atomic stock deduction, and order completion (`FR-08`).

### 2. Run the Test Suite
Using `unittest` (built-in):

```bash
python -m unittest discover -s tests -v
```

Or with `pytest` (if installed):

```bash
pytest -v
```

## Key Engineering Highlights
- **Safety & Collision Avoidance:** `SensorSubsystem` models 20 Hz polling with `< 0.5 m` obstacle rerouting, `<= 0.3 m` hard-stop detection, and `> 60 s` blocked-corridor escalation to `MAINTENANCE`.
- **2-Factor Cargo Security:** `HospitalRobot.unlock_cargo_bay()` enforces both `Staff ID` and `PIN` verification before unlatching.
- **Battery Guards:** Robots with `battery_level <= 20%` automatically return to `CHARGING` after completing an order; only robots with `battery_level > 25%` are eligible for dispatch.
