"""Medicine catalog and real-time inventory management."""

from __future__ import annotations

from typing import List, Optional


class Medicine:
    """Represents a clinical medicine or supply item."""

    def __init__(self, medicine_id: str, name: str, category: str, required_temp: float) -> None:
        self.medicine_id = medicine_id
        self.name = name
        self.category = category
        self.required_temp = required_temp


class InventoryItem:
    """Tracks stock, reserved units, and low-stock threshold for a Medicine."""

    def __init__(self, medicine: Medicine, quantity: int, threshold_limit: int) -> None:
        self.medicine = medicine
        self.quantity = quantity
        self.reserved = 0
        self.threshold_limit = threshold_limit

    @property
    def available_quantity(self) -> int:
        return self.quantity - self.reserved

    def deduct_stock(self, amount: int) -> bool:
        """Finalize stock deduction upon verified delivery."""
        if amount <= 0 or amount > self.quantity:
            return False
        self.quantity -= amount
        self.reserved = max(0, self.reserved - amount)
        return True

    def restock(self, amount: int) -> None:
        """Add stock units to the inventory item."""
        if amount > 0:
            self.quantity += amount

    def is_low_stock(self) -> bool:
        """Return True if available stock has fallen below threshold_limit."""
        return self.available_quantity < self.threshold_limit


class InventoryManager:
    """Centralized real-time inventory service with reservation and alerting."""

    def __init__(self) -> None:
        self.items: List[InventoryItem] = []
        self.alerts: List[str] = []

    def add_item(self, item: InventoryItem) -> None:
        self.items.append(item)

    def find_item(self, medicine_id: str) -> Optional[InventoryItem]:
        for item in self.items:
            if item.medicine.medicine_id == medicine_id:
                return item
        return None

    def check_stock_availability(self, medicine_id: str, requested_qty: int) -> bool:
        """Return True if requested_qty is available without breaching zero stock."""
        if requested_qty <= 0:
            return False
        item = self.find_item(medicine_id)
        if item is None:
            return False
        return item.available_quantity >= requested_qty

    def reserve_items(self, medicine_id: str, quantity: int) -> bool:
        """Reserve stock on order dispatch and trigger alert if below threshold."""
        if not self.check_stock_availability(medicine_id, quantity):
            self.trigger_low_stock_alert(medicine_id)
            return False
        item = self.find_item(medicine_id)
        assert item is not None
        item.reserved += quantity
        if item.is_low_stock():
            self.trigger_low_stock_alert(medicine_id)
        return True

    def trigger_low_stock_alert(self, medicine_id: str) -> None:
        """Record an automated low-stock alert for the pharmacy team."""
        item = self.find_item(medicine_id)
        name = item.medicine.name if item else medicine_id
        qty = item.available_quantity if item else 0
        self.alerts.append(f"LOW STOCK ALERT: {name} ({medicine_id}) — available={qty}")
