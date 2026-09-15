"""Unit tests for Admin Dashboard Order Creation (POST /api/admin/orders)."""

import unittest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.app import app
from src.repositories.sqlite_repo import SqliteRepository


class TestAdminOrderCreation(unittest.TestCase):
    def setUp(self):
        self.repo = SqliteRepository()
        self.tenant_id = "petroil"
        self.client = TestClient(app)

    def test_create_order_immediate_success(self):
        payload = {
            "customer_name": "Don Ramón Valdés",
            "customer_phone": "6691234567",
            "delivery_address": "Calle del Hambre 72, Mazatlán",
            "items": [
                {
                    "product_id": "cilindro-30kg",
                    "product_name": "Cilindro de Gas LP 30 kg",
                    "quantity": 2,
                    "unit_price": 670.0
                }
            ],
            "delivery_schedule": "Lo antes posible",
            "payment_method": "Efectivo",
            "notes": "Casa amarilla con portón negro. Traer cambio de $1500.",
            "dispatch_mode": "none"
        }

        response = self.client.post("/api/admin/orders", json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()
        self.assertTrue(data.get("ok"))
        order_info = data.get("order")
        self.assertIsNotNone(order_info)
        order_id = order_info["id"]

        # Verify in DB
        db_order = self.repo.get_order_by_id(self.tenant_id, order_id)
        self.assertIsNotNone(db_order)
        self.assertEqual(db_order.customer_name, "Don Ramón Valdés")
        self.assertEqual(db_order.customer_phone, "6691234567")
        self.assertEqual(db_order.channel, "dashboard")
        self.assertEqual(db_order.total_amount, 1340.0)
        self.assertEqual(db_order.status, "confirmed")
        self.assertIn("Traer cambio", db_order.notes)

    def test_create_order_assigned_to_driver(self):
        # Find or create a test driver
        drivers = self.client.get("/api/admin/drivers").json()
        if not drivers:
            driver = self.repo.create_driver(
                self.tenant_id,
                name="Chofer Prueba Asignacion",
                phone="6698887766",
                vehicle_type="cilindros",
                vehicle_plate="TEST-99"
            )
            driver_id = driver.id
        else:
            driver_id = drivers[0]["id"]

        payload = {
            "customer_name": "Sra. Florinda Meza",
            "customer_phone": "6695551234",
            "delivery_address": "Privada Las Gaviotas 14, Mazatlán",
            "items": [
                {
                    "product_id": "cilindro-20kg",
                    "product_name": "Cilindro de Gas LP 20 kg",
                    "quantity": 1,
                    "unit_price": 450.0
                }
            ],
            "delivery_schedule": "Lo antes posible",
            "payment_method": "Tarjeta",
            "dispatch_mode": "driver",
            "driver_id": driver_id
        }

        response = self.client.post("/api/admin/orders", json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()
        order_info = data.get("order")
        self.assertEqual(order_info["status"], "assigned")
        self.assertEqual(order_info["driver_id"], driver_id)

        # Verify DB status
        db_order = self.repo.get_order_by_id(self.tenant_id, order_info["id"])
        self.assertEqual(db_order.status, "assigned")
        self.assertEqual(db_order.driver_id, driver_id)

    def test_create_order_scheduled_future(self):
        future_dt = datetime.now() + timedelta(hours=4)
        iso_str = future_dt.isoformat()

        payload = {
            "customer_name": "Profesor Jirafales",
            "customer_phone": "6694443322",
            "delivery_address": "Colegio Primario 45, Mazatlán",
            "items": [
                {
                    "product_id": "estacionario-litros",
                    "product_name": "Gas Estacionario por Litro",
                    "quantity": 150,
                    "unit_price": 13.5
                }
            ],
            "delivery_schedule": "Hoy a las 6:00 PM",
            "scheduled_for": iso_str,
            "payment_method": "Transferencia",
            "dispatch_mode": "none"
        }

        response = self.client.post("/api/admin/orders", json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()
        order_info = data.get("order")
        self.assertEqual(order_info["status"], "scheduled")

        db_order = self.repo.get_order_by_id(self.tenant_id, order_info["id"])
        self.assertEqual(db_order.status, "scheduled")
        self.assertIsNotNone(db_order.scheduled_for)

    def test_create_order_validation_errors(self):
        # Empty items
        payload = {
            "customer_name": "Cliente Sin Items",
            "customer_phone": "6691112233",
            "delivery_address": "Calle 1, Mazatlán",
            "items": []
        }
        res = self.client.post("/api/admin/orders", json=payload)
        self.assertEqual(res.status_code, 422)

        # Missing required customer name
        payload2 = {
            "customer_phone": "6691112233",
            "delivery_address": "Calle 1, Mazatlán",
            "items": [{"product_id": "cilindro-30kg", "quantity": 1}]
        }
        res2 = self.client.post("/api/admin/orders", json=payload2)
        self.assertEqual(res2.status_code, 422)


if __name__ == "__main__":
    unittest.main()
