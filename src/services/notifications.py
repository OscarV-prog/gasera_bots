"""Cross-bot notification service for clients and drivers (Telegram & WhatsApp)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


def _send_telegram_api_call(token: str, method: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Send a request directly to Telegram Bot API and return parsed JSON response."""
    if not token:
        logger.debug(f"[Telegram Notification] No token configured for method {method}.")
        return None

    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status == 200:
                body = resp.read().decode("utf-8")
                return json.loads(body)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        try:
            parsed = json.loads(error_body)
        except Exception:
            parsed = {"ok": False, "error_code": e.code, "description": error_body}

        desc = str(parsed.get("description", "")).lower()
        if "message is not modified" in desc:
            logger.debug(f"Telegram API {method} (not modified): {desc}")
        elif any(k in desc for k in ("message can't be edited", "message to edit not found", "message to delete not found", "chat not found", "bot was blocked by the user", "user is deactivated")):
            logger.info(f"Telegram API {method} (expected/handled): {desc}")
        else:
            logger.warning(f"Telegram API HTTP {e.code} for {method}: {error_body}")
        return parsed
    except Exception as e:
        logger.warning(f"Error sending Telegram notification ({method}): {e}")

    return None


def _send_telegram_api(token: str, method: str, payload: dict[str, Any]) -> bool:
    """Send a request directly to Telegram Bot API via standard HTTP and check success."""
    resp = _send_telegram_api_call(token, method, payload)
    return bool(resp and resp.get("ok"))


def _is_whatsapp_channel(channel_user_id: str, channel: str | None = None) -> bool:
    """Check if the recipient is a WhatsApp user."""
    if channel:
        return channel.lower() == "whatsapp"

    uid_str = str(channel_user_id).strip()
    if not uid_str:
        return False

    clean_digits = re.sub(r"\D", "", uid_str)
    if clean_digits.startswith("52") and len(clean_digits) in (12, 13):
        return True
    if len(clean_digits) == 10 and clean_digits.isdigit():
        return True

    try:
        from src.repositories import get_repository
        repo = get_repository()
        cust = repo.get_customer("petroil", "whatsapp", uid_str)
        if cust:
            return True
        cust_phone = repo.get_customer_by_phone("petroil", clean_digits)
        if cust_phone and getattr(cust_phone, "channel", "") == "whatsapp":
            return True
    except Exception:
        pass

    return False


def _format_markdown_for_whatsapp(text: str) -> str:
    """Convert Telegram Markdown formatting (**bold**) to WhatsApp style (*bold*)."""
    if not text:
        return ""
    # Convert **bold** -> *bold*
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    # Convert __italic__ -> _italic_
    text = re.sub(r"__(.+?)__", r"_\1_", text)
    return text


def _send_whatsapp_message_sync(recipient_wa_id: str, text: str) -> bool:
    """Synchronously send a WhatsApp message using WhatsAppAdapter."""
    from src.channels.whatsapp.adapter import WhatsAppAdapter
    wa = WhatsAppAdapter()
    if not wa.is_configured:
        logger.warning(f"[WhatsApp Notification] Adapter not configured for {recipient_wa_id}")
        return False

    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            loop.create_task(wa.send_text_message(recipient_wa_id, text))
            return True
        else:
            return asyncio.run(wa.send_text_message(recipient_wa_id, text))
    except Exception as e:
        logger.error(f"[WhatsApp Notification] Error sending to {recipient_wa_id}: {e}")
        return False


def _send_whatsapp_location_sync(
    recipient_wa_id: str,
    lat: float,
    lng: float,
    name: str = "Repartidor Petroil en Camino",
    address: str = "",
) -> bool:
    """Synchronously send a WhatsApp location pin using WhatsAppAdapter."""
    from src.channels.whatsapp.adapter import WhatsAppAdapter
    wa = WhatsAppAdapter()
    if not wa.is_configured:
        return False

    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            loop.create_task(wa.send_location(recipient_wa_id, lat, lng, name, address))
            return True
        else:
            return asyncio.run(wa.send_location(recipient_wa_id, lat, lng, name, address))
    except Exception as e:
        logger.error(f"[WhatsApp Location] Error sending to {recipient_wa_id}: {e}")
        return False


def send_client_live_location(
    channel_user_id: str,
    latitude: float,
    longitude: float,
    live_period: int = 7200,
    channel: str | None = None,
) -> int | None:
    """Send a live location pin to the customer via Client Bot (Telegram or WhatsApp) and return the message_id."""
    if not channel_user_id:
        return None

    if _is_whatsapp_channel(channel_user_id, channel):
        # 1. Enviar pin interactivo de mapa de WhatsApp
        _send_whatsapp_location_sync(
            channel_user_id,
            latitude,
            longitude,
            name="📍 Repartidor en Camino (Gas Petroil)",
            address=f"Ruta en vivo hacia tu domicilio (Lat: {latitude:.5f}, Lng: {longitude:.5f})",
        )
        # 2. Enviar mensaje con enlace de seguimiento en tiempo real
        maps_url = f"https://www.google.com/maps?q={latitude:.6f},{longitude:.6f}"
        msg_tracking = (
            f"📍 *¡Tu repartidor va en camino a tu domicilio!*\n\n"
            f"🗺️ Puedes seguir su ubicación en el mapa aquí:\n{maps_url}\n\n"
            f"🚚 Manténte al pendiente para recibir tu servicio."
        )
        _send_whatsapp_message_sync(channel_user_id, msg_tracking)
        return 999999

    # Telegram
    settings = get_settings()
    token = settings.telegram_bot_token
    if not token:
        return None

    payload = {
        "chat_id": channel_user_id,
        "latitude": latitude,
        "longitude": longitude,
        "live_period": live_period,
    }
    resp = _send_telegram_api_call(token, "sendLocation", payload)
    if resp and resp.get("ok"):
        result = resp.get("result", {})
        msg_id = result.get("message_id")
        logger.info(f"📍 Ubicación en tiempo real compartida al cliente {channel_user_id} (msg_id: {msg_id})")
        return msg_id
    return None


def edit_client_live_location(
    channel_user_id: str,
    message_id: int,
    latitude: float,
    longitude: float,
    channel: str | None = None,
) -> bool:
    """Update an existing live location pin in the customer's chat (Telegram live location edit, WhatsApp map update)."""
    if not channel_user_id:
        return False

    if _is_whatsapp_channel(channel_user_id, channel) or message_id == 999999:
        # En WhatsApp confirmamos la recepción exitosa para no desconfigurar la orden en base de datos
        return True

    # Telegram
    settings = get_settings()
    token = settings.telegram_bot_token
    if not token or not message_id:
        return False

    payload = {
        "chat_id": channel_user_id,
        "message_id": message_id,
        "latitude": latitude,
        "longitude": longitude,
    }
    resp = _send_telegram_api_call(token, "editMessageLiveLocation", payload)
    if resp and resp.get("ok"):
        return True
    if resp and "message is not modified" in str(resp.get("description", "")).lower():
        return True
    return False


def remove_client_live_location(channel_user_id: str, message_id: int) -> bool:
    """Delete or stop the live location pin from the customer's chat."""
    if not channel_user_id or not message_id or message_id == 999999:
        return False

    settings = get_settings()
    token = settings.telegram_bot_token
    if not token:
        return False

    # 1. Intentar eliminar el mensaje por completo para limpiar el chat
    delete_payload = {
        "chat_id": channel_user_id,
        "message_id": message_id,
    }
    del_ok = _send_telegram_api(token, "deleteMessage", delete_payload)
    if del_ok:
        logger.info(f"🗑️ Mensaje de ubicación en vivo {message_id} eliminado del chat del cliente {channel_user_id}")
        return True

    # 2. Fallback: detener la transmisión si no se pudo borrar
    stop_payload = {
        "chat_id": channel_user_id,
        "message_id": message_id,
    }
    stop_ok = _send_telegram_api(token, "stopMessageLiveLocation", stop_payload)
    if stop_ok:
        logger.info(f"⏹️ Transmisión de ubicación en vivo {message_id} detenida en chat {channel_user_id}")
    return stop_ok


def notify_client(
    channel_user_id: str,
    message: str,
    reply_markup: dict[str, Any] | None = None,
    channel: str | None = None,
) -> bool:
    """Send an automated notification to the customer via Client Bot (Telegram or WhatsApp)."""
    if not channel_user_id:
        return False

    if _is_whatsapp_channel(channel_user_id, channel):
        wa_text = _format_markdown_for_whatsapp(message)
        return _send_whatsapp_message_sync(channel_user_id, wa_text)

    # Telegram
    settings = get_settings()
    token = settings.telegram_bot_token
    if not token:
        return False

    payload: dict[str, Any] = {
        "chat_id": channel_user_id,
        "text": message,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    ok = _send_telegram_api(token, "sendMessage", payload)
    if not ok:
        payload.pop("parse_mode", None)
        ok = _send_telegram_api(token, "sendMessage", payload)
    return ok


def notify_driver(
    telegram_user_id: str,
    message: str,
    reply_markup: dict[str, Any] | None = None,
    lat: float | None = None,
    lng: float | None = None,
) -> bool:
    """Send an interactive notification and optional location to a driver via Driver Bot."""
    if not telegram_user_id:
        return False

    tid_str = str(telegram_user_id).strip()
    if not tid_str.isdigit():
        logger.debug(f"[notify_driver] Skipping non-numeric telegram_user_id: {telegram_user_id}")
        return False

    settings = get_settings()
    token = settings.telegram_driver_bot_token or settings.telegram_bot_token
    if not token:
        return False

    # 1. Send location pin ONLY if coordinates are valid and NOT the generic city center fallback
    is_fallback = (abs(lat - 23.2014) < 0.0001 and abs(lng - (-106.4215)) < 0.0001) if (lat and lng) else True
    if lat is not None and lng is not None and lat != 0.0 and lng != 0.0 and not is_fallback:
        loc_payload = {
            "chat_id": telegram_user_id,
            "latitude": lat,
            "longitude": lng,
        }
        _send_telegram_api(token, "sendLocation", loc_payload)

    # 2. Send message with interactive action buttons
    payload = {
        "chat_id": telegram_user_id,
        "text": message,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    ok = _send_telegram_api(token, "sendMessage", payload)
    if not ok:
        # Retry without markdown if formatting was rejected by Telegram
        payload.pop("parse_mode", None)
        ok = _send_telegram_api(token, "sendMessage", payload)

    return ok


def notify_delivery_survey(order_id: int, tenant_id: str = "petroil") -> bool:
    """Send delivery completion notification and interactive driver rating survey to the customer (Telegram or WhatsApp)."""
    from src.repositories import get_repository
    repo = get_repository()
    order = repo.get_order_by_id(tenant_id, order_id)
    if not order:
        logger.warning(f"[Delivery Survey] Order #{order_id} not found.")
        return False

    recipient_id = str(order.channel_user_id or order.customer_phone or "").strip()
    if not recipient_id:
        logger.warning(f"[Delivery Survey] Order #{order_id} has no channel_user_id or customer_phone.")
        return False

    driver_desc = ""
    if order.driver_id:
        driver = repo.get_driver(order.driver_id)
        if driver:
            plate_info = f" ({driver.vehicle_plate})" if driver.vehicle_plate else ""
            driver_desc = f"\n👨‍✈️ *Repartidor:* {driver.name}{plate_info}\n"

    # Si el cliente proviene de WhatsApp
    if getattr(order, "channel", "").lower() == "whatsapp" or _is_whatsapp_channel(recipient_id, getattr(order, "channel", None)):
        try:
            from src.channels.whatsapp.adapter import WhatsAppAdapter
            wa_adapter = WhatsAppAdapter()
            if wa_adapter.is_configured:
                msg_wa = (
                    f"📦 *¡Tu pedido #{order_id} ha sido entregado exitosamente!*\n\n"
                    f"💰 *Total pagado:* ${order.total_amount:.2f} {order.currency} ({order.payment_method})"
                    f"{driver_desc}\n"
                    "🌟 *¿Cómo calificarías la atención de tu repartidor?*\n"
                    "Por favor califícalo seleccionando una opción a continuación:"
                )
                buttons = [
                    {"id": f"rate_driver:{order_id}:5", "title": "⭐ 5 Excelente"},
                    {"id": f"rate_driver:{order_id}:4", "title": "⭐ 4 Bueno"},
                    {"id": f"rate_driver:{order_id}:3", "title": "⭐ 1-3 Regular"},
                ]
                
                # 1. Intentar enviar con botones interactivos
                try:
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = None
                    if loop and loop.is_running():
                        loop.create_task(wa_adapter.send_interactive_buttons(recipient_id, msg_wa, buttons))
                        return True
                    else:
                        ok_btn = asyncio.run(wa_adapter.send_interactive_buttons(recipient_id, msg_wa, buttons))
                        if ok_btn:
                            return True
                except Exception as ex:
                    logger.warning(f"[WhatsApp Survey] Interactive buttons failed, falling back to text: {ex}")

                # 2. Fallback garantizado: enviar confirmación de entrega y encuesta en texto plano
                msg_wa_text = (
                    f"📦 *¡Tu pedido #{order_id} ha sido entregado exitosamente!*\n\n"
                    f"💰 *Total pagado:* ${order.total_amount:.2f} {order.currency} ({order.payment_method})"
                    f"{driver_desc}\n"
                    "🌟 *¿Cómo calificarías la atención de tu repartidor?*\n"
                    "Por favor responde a este mensaje con un número del 1 al 5:\n\n"
                    "5️⃣ ⭐⭐⭐⭐⭐ Excelente\n"
                    "4️⃣ ⭐⭐⭐⭐ Bueno\n"
                    "3️⃣ ⭐⭐⭐ Regular\n"
                    "2️⃣ ⭐⭐ Malo\n"
                    "1️⃣ ⭐ Muy malo"
                )
                return _send_whatsapp_message_sync(recipient_id, msg_wa_text)
        except Exception as e:
            logger.error(f"[WhatsApp Survey] Exception: {e}")
            return False

    # Interactive Inline Keyboard with 5 stars (Telegram)
    driver_desc_tg = driver_desc.replace("*", "**")
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "⭐ 1", "callback_data": f"rate_driver:{order_id}:1"},
                {"text": "⭐ 2", "callback_data": f"rate_driver:{order_id}:2"},
                {"text": "⭐ 3", "callback_data": f"rate_driver:{order_id}:3"},
                {"text": "⭐ 4", "callback_data": f"rate_driver:{order_id}:4"},
                {"text": "⭐ 5", "callback_data": f"rate_driver:{order_id}:5"},
            ]
        ]
    }

    msg_cliente = (
        f"📦 **¡Tu pedido #{order_id} ha sido entregado exitosamente!**\n\n"
        f"💰 **Total pagado:** ${order.total_amount:.2f} {order.currency} ({order.payment_method})"
        f"{driver_desc_tg}\n"
        "🌟 **¿Cómo calificarías el servicio y la atención de tu repartidor?**\n"
        "Por favor califícalo tocando una de las estrellas a continuación (1 a 5):"
    )

    return notify_client(recipient_id, msg_cliente, reply_markup=reply_markup, channel="telegram")

