"""Tool: Cancel a customer order and notify the assigned driver if applicable."""

from __future__ import annotations

import logging
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.repositories import get_repository
from src.services.notifications import notify_driver

logger = logging.getLogger(__name__)


@tool
def cancel_order(
    order_id: int,
    reason: str = "Cancelado por el cliente",
    config: RunnableConfig = None,
) -> str:
    """Cancel an active or pending customer order in the system.

    Use this tool when the customer explicitly asks to cancel an existing order.

    Args:
        order_id: The ID / folio number of the order to cancel (e.g. 29).
        reason: Optional reason for cancellation provided by the customer.
    """
    configurable = config.get("configurable", {}) if config else {}
    tenant_id = configurable.get("tenant_id", "petroil")

    repo = get_repository()
    order = repo.get_order_by_id(tenant_id, order_id)

    if not order:
        return f"No se encontró ningún pedido con el folio #{order_id}."

    if order.status == "delivered":
        return f"El pedido #{order_id} ya fue entregado y no puede ser cancelado."

    if order.status == "cancelled":
        return f"El pedido #{order_id} ya se encuentra cancelado."

    # Cancel order in DB and release driver
    cancelled_order = repo.cancel_order(tenant_id, order_id, cancelled_by="el cliente", reason=reason)

    # If driver was assigned and has telegram, notify them immediately
    if order.driver_id:
        driver = repo.get_driver(order.driver_id)
        if driver and driver.telegram_user_id:
            msg_driver = (
                f"❌ **PEDIDO #{order_id} CANCELADO**\n\n"
                f"👤 Cliente: {order.customer_name}\n"
                f"📍 Dirección: {order.delivery_address}\n"
                f"📝 Motivo: {reason}\n\n"
                "El cliente ha cancelado este pedido. Ya no es necesario acudir al domicilio. Has quedado disponible para otros viajes."
            )
            notify_driver(driver.telegram_user_id, msg_driver)

    return (
        f"✅ El pedido con folio #{order_id} ha sido CANCELADO exitosamente.\n"
        f"Confirma al cliente que su pedido #{order_id} quedó cancelado sin ningún cargo."
    )
