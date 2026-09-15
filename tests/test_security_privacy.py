import os
import unittest
from langchain_core.runnables import RunnableConfig

from src.database import init_db
from src.repositories import get_repository
from src.tools.customer_info import get_customer_info
from src.tools.get_order_status import get_order_status
from telegram_bot import optimizar_respuesta_con_botones


class TestSecurityAndPrivacy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DATA_SOURCE"] = "sqlite"
        init_db()
        cls.repo = get_repository()

        # Seed test customer A and B
        cls.repo.save_or_update_customer(
            tenant_id="petroil",
            channel="telegram",
            channel_user_id="user_tg_111",
            name="Oscar Vizcarra",
            phone="6699123501",
            address="Calle Privada 100, Mazatlán",
        )
        cls.repo.save_or_update_customer(
            tenant_id="petroil",
            channel="telegram",
            channel_user_id="user_tg_222",
            name="Francisco Rojo",
            phone="6691232448",
            address="Av Central 500, Mazatlán",
        )

    def test_customer_info_does_not_leak_raw_addresses(self):
        """get_customer_info must never print raw physical street addresses in tool text."""
        config: RunnableConfig = {
            "configurable": {
                "tenant_id": "petroil",
                "channel": "telegram",
                "channel_user_id": "user_tg_111",
            }
        }
        res = get_customer_info.invoke({"phone": "6699123501"}, config=config)
        self.assertIn("CLIENTE RECONOCIDO", res)
        # Should not include the raw street address in tool output
        self.assertNotIn("Calle Privada 100", res)
        self.assertIn("NUNCA listes direcciones físicas", res)

    def test_customer_info_blocks_third_party_phone_lookup(self):
        """A user bound to user_tg_111 (6699123501) cannot query 6691232448."""
        config: RunnableConfig = {
            "configurable": {
                "tenant_id": "petroil",
                "channel": "telegram",
                "channel_user_id": "user_tg_111",
            }
        }
        res = get_customer_info.invoke({"phone": "6691232448"}, config=config)
        self.assertIn("ACCESO DENEGADO", res)
        self.assertNotIn("Francisco Rojo", res)

    def test_customer_info_blocks_multiple_phone_numbers(self):
        """Batch / multi-phone queries must be rejected."""
        config: RunnableConfig = {
            "configurable": {
                "tenant_id": "petroil",
                "channel": "telegram",
                "channel_user_id": "user_tg_111",
            }
        }
        res = get_customer_info.invoke({"phone": "6691232448 y 6699123501"}, config=config)
        self.assertIn("ACCESO DENEGADO", res)

    def test_order_status_blocks_third_party_phone_lookup(self):
        """User user_tg_111 cannot query orders for phone 6691232448."""
        config: RunnableConfig = {
            "configurable": {
                "tenant_id": "petroil",
                "channel": "telegram",
                "channel_user_id": "user_tg_111",
            }
        }
        res = get_order_status.invoke({"phone": "6691232448"}, config=config)
        self.assertIn("ACCESO DENEGADO", res)

    def test_order_status_blocks_multiple_phone_numbers(self):
        """Querying multiple phone numbers in get_order_status must be rejected."""
        config: RunnableConfig = {
            "configurable": {
                "tenant_id": "petroil",
                "channel": "telegram",
                "channel_user_id": "user_tg_111",
            }
        }
        res = get_order_status.invoke({"phone": "6691232448 y 6699123501"}, config=config)
        self.assertIn("ACCESO DENEGADO", res)

    def test_order_status_does_not_leak_address_in_summary(self):
        """Order status summary for own orders must not contain full street address."""
        order = self.repo.create_order(
            tenant_id="petroil",
            customer_name="Oscar Vizcarra",
            customer_phone="6699123501",
            delivery_address="Calle Privada 100, Mazatlán",
            items=[{"product_name": "Cilindro de Gas LP 30 kg", "quantity": 1}],
            channel="telegram",
            channel_user_id="user_tg_111",
        )
        config: RunnableConfig = {
            "configurable": {
                "tenant_id": "petroil",
                "channel": "telegram",
                "channel_user_id": "user_tg_111",
            }
        }
        res = get_order_status.invoke({"order_id": order.id}, config=config)
        self.assertIn(f"Pedido #{order.id}", res)
        self.assertNotIn("Calle Privada 100", res)
        self.assertNotIn("Método de pago", res)
        self.assertNotIn("Efectivo", res)

    def test_optimizar_respuesta_con_botones_strips_address_blocks(self):
        """telegram_bot text optimizer must strip any address lists from outgoing messages."""
        msg = (
            "¡Hola, Oscar!\n\n"
            "📍 **Tus direcciones registradas:**\n"
            "1. 📍 Calle Secreta 456, Mazatlán\n"
            "2. 📍 Av Las Torres 789, Mazatlán\n\n"
            "¿A cuál deseas que enviemos?"
        )
        cleaned = optimizar_respuesta_con_botones(msg, None)
        self.assertNotIn("Tus direcciones registradas", cleaned)
        self.assertNotIn("Calle Secreta 456", cleaned)
        self.assertNotIn("Av Las Torres 789", cleaned)

    def test_order_history_does_not_trigger_payment_buttons(self):
        """Order history query responses must not attach payment buttons in WhatsApp or Telegram."""
        from src.channels.whatsapp.adapter import WhatsAppAdapter
        from telegram_bot import detectar_botones_mensaje

        adapter = WhatsAppAdapter()
        sample_history_msg = (
            "¡Hola Oscar Vizcarra! 👋 Claro que sí, con gusto te comparto el historial de tus pedidos registrados en tu cuenta. 📦\n\n"
            "Encontré *10 pedidos* en tu historial. Te muestro el detalle:\n\n"
            "📦 *Pedido #412* — ✅ Confirmado — Lo antes posible\n"
            "• 1x Cilindro de Gas LP 30 kg — *Total: $670.00 MXN*\n"
        )
        cleaned, spec = adapter.detect_interactive_elements(sample_history_msg, phone="6699123501", channel_user_id="5216699123501")
        self.assertIsNone(spec)

    def test_create_order_deterministic_pricing_and_bounds(self):
        """create_order must force catalog prices, reject negative quantities and quantities > 50."""
        from src.tools.create_order import create_order
        config: RunnableConfig = {
            "configurable": {
                "tenant_id": "petroil",
                "channel": "telegram",
                "channel_user_id": "user_tg_111",
            }
        }
        # Intent of price tampering (trying to buy 30kg cylinder for $0.01)
        res = create_order.invoke({
            "customer_name": "Oscar Vizcarra",
            "customer_phone": "6699123501",
            "delivery_address": "Calle Privada 100",
            "items": [{"product_name": "Cilindro de Gas LP 30 kg", "quantity": 1, "unit_price": 0.01}],
        }, config=config)
        self.assertIn("PEDIDO REGISTRADO EXITOSAMENTE", res)
        # Verify order in DB has the real price from catalog (e.g. >= 500), not 0.01
        import re
        m = re.search(r"#(\d+)", res)
        self.assertTrue(m)
        order_id = int(m.group(1))
        order = self.repo.get_order_by_id("petroil", order_id)
        self.assertEqual(order.items[0].unit_price, 670.0)
        self.assertEqual(order.total_amount, 670.0)

        # Test negative quantity
        neg_res = create_order.invoke({
            "customer_name": "Oscar Vizcarra",
            "customer_phone": "6699123501",
            "delivery_address": "Calle Privada 100",
            "items": [{"product_name": "Cilindro de Gas LP 30 kg", "quantity": -5}],
        }, config=config)
        self.assertIn("Error de seguridad", neg_res)

        # Test excessive quantity (>50)
        max_res = create_order.invoke({
            "customer_name": "Oscar Vizcarra",
            "customer_phone": "6699123501",
            "delivery_address": "Calle Privada 100",
            "items": [{"product_name": "Cilindro de Gas LP 30 kg", "quantity": 100}],
        }, config=config)
        self.assertIn("cantidad máxima permitida", max_res)

    def test_cancel_order_bola_protection(self):
        """User B cannot cancel an order created by User A."""
        from src.tools.cancel_order import cancel_order
        order_a = self.repo.create_order(
            tenant_id="petroil",
            customer_name="Oscar Vizcarra",
            customer_phone="6699123501",
            delivery_address="Calle Privada 100, Mazatlán",
            items=[{"product_name": "Cilindro de Gas LP 30 kg", "quantity": 1, "unit_price": 670.0}],
            channel="telegram",
            channel_user_id="user_tg_111",
        )
        # Attempt by user B (user_tg_222) to cancel order A
        config_b: RunnableConfig = {
            "configurable": {
                "tenant_id": "petroil",
                "channel": "telegram",
                "channel_user_id": "user_tg_222",
            }
        }
        res_b = cancel_order.invoke({"order_id": order_a.id}, config=config_b)
        self.assertIn("ACCESO DENEGADO", res_b)

        # Confirm order remains active
        order_check = self.repo.get_order_by_id("petroil", order_a.id)
        self.assertNotEqual(order_check.status, "cancelled")

        # Legitimate cancellation by user A
        config_a: RunnableConfig = {
            "configurable": {
                "tenant_id": "petroil",
                "channel": "telegram",
                "channel_user_id": "user_tg_111",
            }
        }
        res_a = cancel_order.invoke({"order_id": order_a.id}, config=config_a)
        self.assertIn("CANCELADO exitosamente", res_a)

    def test_whatsapp_hmac_signature_and_idempotency(self):
        """WhatsApp HMAC signature validation and duplicate message caching."""
        import hashlib
        import hmac
        from src.channels.whatsapp.router import verify_whatsapp_signature, _is_duplicate_message

        secret = "test_meta_secret_key"
        body = b'{"object":"whatsapp_business_account"}'
        valid_hash = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        invalid_hash = "sha256=invalidhash000000000000000000000000000"

        self.assertTrue(verify_whatsapp_signature(body, valid_hash, secret))
        self.assertFalse(verify_whatsapp_signature(body, invalid_hash, secret))
        self.assertFalse(verify_whatsapp_signature(body, None, secret))

        # Idempotency
        msg_id = "test_unique_msg_12345"
        self.assertFalse(_is_duplicate_message(msg_id))  # First time is NOT duplicate
        self.assertTrue(_is_duplicate_message(msg_id))   # Second time IS duplicate


if __name__ == "__main__":
    unittest.main()

