import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient

from src.app import app
from src.channels.whatsapp.adapter import WhatsAppAdapter
from src.config.settings import get_settings


def test_whatsapp_webhook_verification_success(client):
    """Test Meta webhook verification GET with matching verify_token."""
    settings = get_settings()
    token = settings.whatsapp_verify_token or "petroil_gas_webhook_secret"
    challenge = "1158201444"

    response = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": token,
            "hub.challenge": challenge,
        },
    )
    assert response.status_code == 200
    assert response.text == challenge


def test_whatsapp_webhook_verification_failure(client):
    """Test Meta webhook verification GET with invalid token."""
    response = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token_123",
            "hub.challenge": "1158201444",
        },
    )
    assert response.status_code == 403


def test_adapter_parse_text_message():
    """Test parsing a raw Meta incoming text message."""
    adapter = WhatsAppAdapter()
    raw_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID_TEST",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "526691234567",
                                "phone_number_id": "1234567890",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Juan Perez"},
                                    "wa_id": "5216699123456",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "5216699123456",
                                    "id": "wamid.HBgLTEST12345",
                                    "timestamp": "1725890000",
                                    "type": "text",
                                    "text": {"body": "Hola, buenas tardes quiero pedir gas"},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    events = adapter.parse_webhook_events(raw_payload)
    assert len(events) == 1
    ev = events[0]
    assert ev["msg_id"] == "wamid.HBgLTEST12345"
    assert ev["wa_id"] == "5216699123456"
    assert ev["name"] == "Juan Perez"
    assert ev["type"] == "text"
    assert ev["text"] == "Hola, buenas tardes quiero pedir gas"
    assert WhatsAppAdapter.extract_10_digit_phone(ev["wa_id"]) == "6699123456"


def test_adapter_parse_location_message():
    """Test parsing a raw Meta incoming location pin."""
    adapter = WhatsAppAdapter()
    raw_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID_TEST",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "5216699123456",
                                    "id": "wamid.HBgLLOC12345",
                                    "timestamp": "1725890000",
                                    "type": "location",
                                    "location": {
                                        "latitude": 23.23456,
                                        "longitude": -106.41234,
                                        "name": "Mi Casa",
                                        "address": "Av del Mar 100",
                                    },
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    events = adapter.parse_webhook_events(raw_payload)
    assert len(events) == 1
    ev = events[0]
    assert ev["type"] == "location"
    assert ev["location"]["latitude"] == 23.23456
    assert ev["location"]["longitude"] == -106.41234


def test_adapter_parse_button_reply():
    """Test parsing interactive button reply."""
    adapter = WhatsAppAdapter()
    raw_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID_TEST",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "5216699123456",
                                    "id": "wamid.HBgLBTN12345",
                                    "timestamp": "1725890000",
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {
                                            "id": "client_confirm:yes",
                                            "title": "✅ Confirmar Pedido",
                                        },
                                    },
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    events = adapter.parse_webhook_events(raw_payload)
    assert len(events) == 1
    ev = events[0]
    assert ev["interactive_id"] == "client_confirm:yes"
    assert ev["text"] == "✅ Confirmar Pedido"


def test_adapter_parse_list_reply():
    """Test parsing interactive list menu reply."""
    adapter = WhatsAppAdapter()
    raw_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID_TEST",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "5216699123456",
                                    "id": "wamid.HBgLLIST12345",
                                    "timestamp": "1725890000",
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "list_reply",
                                        "list_reply": {
                                            "id": "client_addr:1",
                                            "title": "1. 📍 Casa",
                                            "description": "Av Insurgentes 450",
                                        },
                                    },
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    events = adapter.parse_webhook_events(raw_payload)
    assert len(events) == 1
    ev = events[0]
    assert ev["interactive_id"] == "client_addr:1"
    assert ev["text"] == "1. 📍 Casa"


from unittest.mock import patch

def test_whatsapp_webhook_post_queued(client):
    """Test POST /webhooks/whatsapp receives payload and returns 200 immediately."""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "526691112233",
                                    "id": "wamid.TEST999",
                                    "type": "text",
                                    "text": {"body": "Hola"},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    with patch("src.channels.whatsapp.router.process_whatsapp_event") as mock_process:
        response = client.post("/webhooks/whatsapp", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["events_queued"] == 1


def test_cart_management():
    """Test shopping cart accumulation, totals calculation, and clearing."""
    from src.channels.whatsapp.router import add_to_cart, clear_cart, format_cart_summary, get_user_cart

    test_wa_id = "test_cart_user_123"
    clear_cart(test_wa_id)
    assert get_user_cart(test_wa_id) == {}

    # Add 1x 20kg cylinder
    add_to_cart(test_wa_id, "gas-lp-20kg", 1)
    # Add 2x 30kg cylinders
    add_to_cart(test_wa_id, "gas-lp-30kg", 2)

    cart = get_user_cart(test_wa_id)
    assert cart["gas-lp-20kg"] == 1
    assert cart["gas-lp-30kg"] == 2

    summary, total_price, total_qty = format_cart_summary(cart, "petroil")
    assert total_qty == 3
    assert total_price == (1 * 450.0 + 2 * 670.0)  # 450 + 1340 = 1790.0
    assert "20 kg" in summary
    assert "30 kg" in summary
    assert "1,790.00" in summary

    clear_cart(test_wa_id)
    assert get_user_cart(test_wa_id) == {}


def test_get_product_by_id():
    """Test get_product_by_id repository method."""
    from src.repositories import get_repository
    repo = get_repository()
    prod = repo.get_product_by_id("petroil", "gas-lp-20kg")
    assert prod is not None
    assert prod.id == "gas-lp-20kg"
    assert prod.price == 450.0

    non_prod = repo.get_product_by_id("petroil", "non_existing_product_xyz")
    assert non_prod is None


if __name__ == "__main__":
    c = TestClient(app)
    print("▶️ Probando verificación de webhook GET exitosa...")
    test_whatsapp_webhook_verification_success(c)
    print("▶️ Probando verificación de webhook GET fallida (token inválido)...")
    test_whatsapp_webhook_verification_failure(c)
    print("▶️ Probando parsing de mensaje de texto WhatsApp...")
    test_adapter_parse_text_message()
    print("▶️ Probando parsing de ubicación GPS WhatsApp...")
    test_adapter_parse_location_message()
    print("▶️ Probando parsing de botón interactivo WhatsApp...")
    test_adapter_parse_button_reply()
    print("▶️ Probando parsing de menú de lista interactiva WhatsApp...")
    test_adapter_parse_list_reply()
    print("▶️ Probando endpoint POST /webhooks/whatsapp...")
    test_whatsapp_webhook_post_queued(c)
    print("▶️ Probando gestión de carrito multi-producto...")
    test_cart_management()
    print("▶️ Probando consulta de producto por ID...")
    test_get_product_by_id()
    print("✅ ¡TODOS LOS TESTS DE WHATSAPP PASARON SATISFACTORIAMENTE!")
