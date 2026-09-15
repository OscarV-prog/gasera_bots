"""Tool: lookup or check existing customer information and previous orders in SQLite."""

from __future__ import annotations

import re
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.repositories import get_repository


from src.services.geocoding import resolve_gps_address_to_name


@tool
def get_customer_info(
    phone: str = "",
    config: RunnableConfig = None,
) -> str:
    """Lookup customer profile, past orders history, and saved delivery addresses in SQLite.

    Use this tool whenever a customer provides their phone number or when starting an order.

    Args:
        phone: The customer's contact phone number to search for.
    """
    configurable = config.get("configurable", {}) if config else {}
    tenant_id = configurable.get("tenant_id", "petroil")
    channel = configurable.get("channel", "telegram")
    channel_user_id = str(configurable.get("channel_user_id", ""))

    repo = get_repository()
    clean_phone = re.sub(r"\D", "", phone) if phone else ""

    # Detectar si se intenta consultar múltiples números a la vez
    if phone and (len(re.findall(r"\b\d{7,12}\b", phone)) > 1 or any(sep in phone for sep in [",", ";", " y ", " and "])):
        return (
            "⛔ ACCESO DENEGADO: Por políticas de privacidad y protección de datos, "
            "no puedes consultar información de múltiples números telefónicos a la vez. "
            "Informa al cliente de forma amable que no puedes procesar consultas de números ajenos ni acceder arbitrariamente a datos, "
            "y recuérdale tus opciones de atención al cliente (Realizar pedido, Consultar su propio pedido o Cancelar)."
        )

    # Verificación de identidad / autorización en canales conversacionales
    if channel and channel_user_id and channel_user_id not in ("admin_manual", "dashboard", "cli_user"):
        bound_customer = repo.get_customer(tenant_id, channel, channel_user_id)
        if bound_customer and bound_customer.phone:
            clean_bound = re.sub(r"\D", "", bound_customer.phone)
            if clean_phone and len(clean_phone) >= 7:
                clean_q_10 = clean_phone[-10:] if len(clean_phone) >= 10 else clean_phone
                clean_b_10 = clean_bound[-10:] if len(clean_bound) >= 10 else clean_bound
                if clean_q_10 != clean_b_10:
                    return (
                        "⛔ ACCESO DENEGADO: Por motivos de seguridad y privacidad, "
                        "no tienes autorización para consultar la información de otro número telefónico. "
                        "Informa al cliente amablemente que solo puedes consultar su propia cuenta vinculada."
                    )

    customer = None

    # 1. Si el usuario proporcionó un teléfono, buscar EXCLUSIVAMENTE por ese teléfono
    if clean_phone and len(clean_phone) >= 7:
        customer = repo.get_customer_by_phone(tenant_id, clean_phone)
    # 2. Si NO se proporcionó teléfono, buscar si el usuario de WhatsApp/Telegram tiene una cuenta previa
    elif not phone and channel and channel_user_id:
        customer = repo.get_customer(tenant_id, channel, channel_user_id)
        if not customer:
            clean_uid = re.sub(r"\D", "", channel_user_id)
            if len(clean_uid) >= 10:
                customer = repo.get_customer_by_phone(tenant_id, clean_uid[-10:])

    # Si encontramos al cliente en la base de datos
    if customer and (customer.name or customer.phone or customer.addresses or customer.address):
        # Buscar historial de pedidos previos del cliente
        past_orders = repo.get_orders_by_customer_phone(tenant_id, customer.phone, limit=3)
        
        lines = [
            "✅ CLIENTE RECONOCIDO EN BASE DE DATOS (CLIENTE FRECUENTE):",
            f"- Nombre: {customer.name}",
            f"- Teléfono registrado: {customer.phone}",
        ]

        if past_orders:
            lines.append(f"\n📦 HISTORIAL: El cliente ya ha realizado {len(past_orders)} pedido(s) anteriormente.")
            last_o = past_orders[0]
            items_str = ", ".join(f"{it.quantity}x {it.product_name}" for it in last_o.items)
            lines.append(f"  • Último pedido: Folio #{last_o.id} ({items_str}) - Total: ${last_o.total_amount:.2f} [{last_o.status}]")
        else:
            lines.append("\n📦 HISTORIAL: Cliente registrado (sin pedidos previos completados).")

        num_addrs = len(customer.addresses) if customer.addresses else (1 if customer.address else 0)
        if num_addrs > 0:
            lines.append(
                f"\n📍 DIRECCIONES: El cliente tiene {num_addrs} dirección(es) guardada(s) en su cuenta. "
                "Para proteger la privacidad y seguridad del cliente, NUNCA listes direcciones físicas completas ni nombres de calle en el chat; "
                "indícale que puede seleccionar su dirección habitual mediante los botones interactivos o registrar una nueva."
            )

        return "\n".join(lines)

    # Si NO se encontró al cliente (teléfono nuevo)
    phone_label = f" ({phone})" if phone else ""
    return f"ℹ️ CLIENTE NUEVO: No existe cuenta registrada previa para {phone_label or 'este teléfono'}."

