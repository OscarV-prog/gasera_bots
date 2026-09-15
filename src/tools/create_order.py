"""Tool: create and register a customer order in SQLite, triggering driver dispatch."""

from __future__ import annotations

import logging
from typing import Any
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.repositories import get_repository
from src.services.dispatch import dispatch_order
from src.services.geocoding import resolve_gps_address_to_name, reverse_geocode

logger = logging.getLogger(__name__)


@tool
def create_order(
    customer_name: str,
    customer_phone: str,
    delivery_address: str,
    items: list[dict[str, Any]],
    delivery_schedule: str = "Lo antes posible",
    payment_method: str = "Efectivo",
    notes: str = "",
    delivery_lat: float | None = None,
    delivery_lng: float | None = None,
    config: RunnableConfig = None,
) -> str:
    """Registra y confirma formalmente un pedido de gas en la base de datos.

    Llama a esta herramienta ÚNICAMENTE tras confirmación afirmativa del cliente.

    Args:
        customer_name: Nombre completo del cliente.
        customer_phone: Teléfono celular del cliente.
        delivery_address: Dirección completa de entrega con calle, número y colonia.
        items: Lista de productos pedidos, ej: [{"product_name": "Cilindro de Gas LP 30 kg", "quantity": 1}].
        delivery_schedule: Horario de entrega (ej. "Hoy a las 5:00 PM", "Lo antes posible").
        payment_method: Método de pago ("Efectivo" o "Terminal").
        notes: Referencias o notas del domicilio.
        delivery_lat: Latitud GPS opcional.
        delivery_lng: Longitud GPS opcional.
    """
    configurable = config.get("configurable", {}) if config else {}
    tenant_id = configurable.get("tenant_id", "petroil")
    channel = configurable.get("channel", "telegram")
    channel_user_id = configurable.get("channel_user_id", "")

    if not customer_name or not customer_phone or not delivery_address:
        return (
            "Error: Para crear el pedido se requiere obligatoriamente: "
            "nombre del cliente, teléfono y dirección de entrega completa."
        )

    if not items:
        return "Error: No se especificaron productos para el pedido."

    repo = get_repository()

    try:
        # Sanitizar teléfono del cliente
        import re
        clean_phone_digits = re.sub(r"\D", "", customer_phone)
        if len(clean_phone_digits) < 7 or len(clean_phone_digits) > 15:
            return "Error: El número de teléfono proporcionado no es válido. Debe contener al menos 7 a 10 dígitos."

        # Validación determinista de catálogo, precios y cantidades
        official_products = repo.get_all_products(tenant_id)
        prods_by_id = {p.id: p for p in official_products}
        prods_by_name = {p.name.lower(): p for p in official_products}

        validated_items = []
        for it in items:
            p_name = it.get("product_name") or it.get("name") or it.get("product_id") or ""
            p_id = it.get("product_id") or ""
            try:
                qty = float(it.get("quantity", 1))
            except (ValueError, TypeError):
                qty = 1.0

            if qty <= 0:
                return f"Error de seguridad: La cantidad para '{p_name}' debe ser mayor a 0."
            if qty > 50:
                return f"Error: La cantidad máxima permitida por pedido minorista es de 50 unidades. Para pedidos de mayoreo, por favor contacta a un asesor."

            # Buscar en catálogo oficial
            matched_prod = prods_by_id.get(p_id) or prods_by_name.get(p_name.lower())
            if not matched_prod:
                # Búsqueda parcial por nombre
                for p in official_products:
                    if p.name.lower() in p_name.lower() or p_name.lower() in p.name.lower():
                        matched_prod = p
                        break

            if matched_prod:
                if not matched_prod.in_stock:
                    return f"Aviso: El producto '{matched_prod.name}' se encuentra temporalmente agotado."
                validated_items.append({
                    "product_id": matched_prod.id,
                    "product_name": matched_prod.name,
                    "quantity": int(qty) if qty.is_integer() else qty,
                    "unit_price": matched_prod.price,  # PRECIO DETERMINISTA FORZADO DE BD
                })
            else:
                validated_items.append({
                    "product_id": p_id or "cilindro-gas",
                    "product_name": p_name or "Cilindro de Gas LP",
                    "quantity": int(qty) if qty.is_integer() else qty,
                })

        clean_addr = resolve_gps_address_to_name(delivery_address.strip())
        if (not clean_addr or clean_addr.lower().startswith("ubicaci")) and delivery_lat is not None and delivery_lng is not None:
            resolved = reverse_geocode(delivery_lat, delivery_lng)
            if resolved and not resolved.lower().startswith("ubicaci"):
                clean_addr = f"{resolved} - {notes.strip()}" if notes.strip() else resolved

        order = repo.create_order(
            tenant_id=tenant_id,
            customer_name=customer_name.strip(),
            customer_phone=customer_phone.strip(),
            delivery_address=clean_addr,
            items=validated_items,
            delivery_schedule=delivery_schedule.strip() if delivery_schedule else "Lo antes posible",
            payment_method=payment_method.strip() if payment_method else "Efectivo",
            notes=notes.strip(),
            channel=channel,
            channel_user_id=channel_user_id,
            delivery_lat=delivery_lat,
            delivery_lng=delivery_lng,
        )

        # La orden queda registrada (o programada en agenda si es a futuro)
        updated_order = repo.get_order_by_id(tenant_id, order.id) or order

        if updated_order.status == "scheduled":
            return (
                f"🗓️ ¡PEDIDO PROGRAMADO CON ÉXITO EN AGENDA!\n\n"
                f"{updated_order.to_display()}\n\n"
                f"Indica al cliente su número de folio (#{order.id}) y confirma que su pedido quedó agendado para: {updated_order.delivery_schedule}. "
                f"Infórmale que nuestra Torre de Control activará la unidad de reparto 30 minutos antes de su horario pactado para garantizar su entrega puntual."
            )

        return (
            f"✅ ¡PEDIDO REGISTRADO EXITOSAMENTE EN BASE DE DATOS!\n\n"
            f"{updated_order.to_display()}\n\n"
            f"Indica al cliente su número de folio (#{order.id}), confirma el horario de entrega y el método de pago registrado. "
            f"Infórmale que nuestra Torre de Control está coordinando la unidad de reparto para su servicio."
        )
    except Exception as e:
        return f"Error al registrar el pedido en la base de datos: {e}"
