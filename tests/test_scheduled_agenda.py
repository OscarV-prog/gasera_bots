"""Unit tests for Scheduled Orders Agenda and 30-minute Pre-Deadline Activation."""

import unittest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.app import app
from src.repositories.sqlite_repo import SqliteRepository, parse_schedule_deadline


class TestScheduledAgenda(unittest.TestCase):
    def setUp(self):
        self.repo = SqliteRepository()
        self.tenant_id = "petroil"
        self.client = TestClient(app)

    def test_parse_schedule_deadline(self):
        ref = datetime(2026, 9, 3, 14, 0, 0)
        
        # Hoy a las 5:00 PM -> 2026-09-03 17:00
        dt = parse_schedule_deadline("Hoy a las 5:00 PM", ref)
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 9)
        self.assertEqual(dt.day, 3)
        self.assertEqual(dt.hour, 17)
        self.assertEqual(dt.minute, 0)

        # Mañana a las 10:30 AM -> 2026-09-04 10:30
        dt2 = parse_schedule_deadline("Mañana a las 10:30 AM", ref)
        self.assertIsNotNone(dt2)
        self.assertEqual(dt2.day, 4)
        self.assertEqual(dt2.hour, 10)
        self.assertEqual(dt2.minute, 30)

        # Lo antes posible -> None (immediate)
        dt3 = parse_schedule_deadline("Lo antes posible", ref)
        self.assertIsNone(dt3)

    def test_future_order_stays_in_agenda_and_not_in_active_table(self):
        now = datetime.now()
        # Scheduled for 3 hours from now (> 30 min)
        future_dt = now + timedelta(hours=3)
        schedule_text = f"Hoy a las {future_dt.strftime('%I:%M %p')}"

        order = self.repo.create_order(
            tenant_id=self.tenant_id,
            customer_name="Cliente Test Agenda Futuro",
            customer_phone="6699990001",
            delivery_address="Av. Del Mar 123, Mazatlán",
            items=[{"product_name": "Cilindro de Gas LP 30 kg", "quantity": 1, "unit_price": 650.0}],
            delivery_schedule=schedule_text,
            scheduled_for=future_dt.isoformat(),
        )

        self.assertIsNotNone(order.id)
        self.assertEqual(order.status, "scheduled")
        self.assertIsNotNone(order.scheduled_for)

        # Verify it appears in the Agenda
        agenda = self.repo.get_scheduled_agenda(self.tenant_id)
        agenda_ids = [item["id"] for item in agenda]
        self.assertIn(order.id, agenda_ids)

        # Locate item in agenda and verify computed properties
        agenda_item = next(item for item in agenda if item["id"] == order.id)
        self.assertFalse(agenda_item["is_activated"])
        self.assertGreater(agenda_item["minutes_until_activation"], 0)

        # Verify it DOES NOT appear in the active orders table (because it's > 30m away)
        active_orders = self.repo.get_all_orders_admin(self.tenant_id, status="active")
        active_ids = [o["id"] for o in active_orders]
        self.assertNotIn(order.id, active_ids)

    def test_order_within_30_minutes_is_activated_in_orders_table(self):
        now = datetime.now()
        # Scheduled for 15 minutes from now (<= 30 min)
        soon_dt = now + timedelta(minutes=15)
        schedule_text = f"Hoy a las {soon_dt.strftime('%I:%M %p')}"

        order = self.repo.create_order(
            tenant_id=self.tenant_id,
            customer_name="Cliente Test Proximo",
            customer_phone="6699990002",
            delivery_address="Zona Dorada 456, Mazatlán",
            items=[{"product_name": "Cilindro de Gas LP 20 kg", "quantity": 1, "unit_price": 450.0}],
            delivery_schedule=schedule_text,
            scheduled_for=soon_dt.isoformat(),
        )

        # Because it is within 30 min, initial_status should be confirmed and active
        self.assertEqual(order.status, "confirmed")

        # Verify it appears in active orders table
        active_orders = self.repo.get_all_orders_admin(self.tenant_id, status="active")
        active_ids = [o["id"] for o in active_orders]
        self.assertIn(order.id, active_ids)

    def test_manual_activate_now_endpoint(self):
        now = datetime.now()
        # Create order scheduled 4 hours from now
        future_dt = now + timedelta(hours=4)
        order = self.repo.create_order(
            tenant_id=self.tenant_id,
            customer_name="Cliente Test Manual Activate",
            customer_phone="6699990003",
            delivery_address="Centro Histórico 789, Mazatlán",
            items=[{"product_name": "Cilindro de Gas LP 30 kg", "quantity": 1, "unit_price": 650.0}],
            delivery_schedule="Hoy en la tarde",
            scheduled_for=future_dt.isoformat(),
        )

        self.assertEqual(order.status, "scheduled")

        # Call POST /api/admin/orders/{id}/activate-now
        res = self.client.post(f"/api/admin/orders/{order.id}/activate-now")
        self.assertEqual(res.status_code, 200)

        # Verify it is now confirmed, assigned or in_route (active)
        updated = self.repo.get_order_by_id(self.tenant_id, order.id)
        self.assertIn(updated.status, ("confirmed", "assigned", "in_route"))

        # And appears in active orders
        active_orders = self.repo.get_all_orders_admin(self.tenant_id, status="active", limit=200)
        active_ids = [o["id"] for o in active_orders]
        self.assertIn(order.id, active_ids)

    def test_reschedule_endpoint(self):
        now = datetime.now()
        order = self.repo.create_order(
            tenant_id=self.tenant_id,
            customer_name="Cliente Test Reschedule",
            customer_phone="6699990004",
            delivery_address="Marina Mazatlán 101",
            items=[{"product_name": "Gas Estacionario 200L", "quantity": 1, "unit_price": 2600.0}],
            delivery_schedule="Hoy a las 4:00 PM",
        )

        # Reschedule for tomorrow 11:00 AM
        tomorrow_11am = (now + timedelta(days=1)).replace(hour=11, minute=0, second=0, microsecond=0)
        res = self.client.post(
            f"/api/admin/orders/{order.id}/reschedule",
            json={
                "delivery_schedule": "Mañana a las 11:00 AM",
                "scheduled_for": tomorrow_11am.isoformat(),
            }
        )
        self.assertEqual(res.status_code, 200)

        updated = self.repo.get_order_by_id(self.tenant_id, order.id)
        self.assertEqual(updated.delivery_schedule, "Mañana a las 11:00 AM")
        self.assertEqual(updated.status, "scheduled")

        agenda = self.repo.get_scheduled_agenda(self.tenant_id)
        item = next((x for x in agenda if x["id"] == order.id), None)
        self.assertIsNotNone(item)
        self.assertIn("Mañana", item["deadline_display"])


if __name__ == "__main__":
    unittest.main()
