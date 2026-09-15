import re
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.models.order import Order
from src.repositories import get_repository


def _to_safe_order_display(order: Order) -> str:
    """Format order summary securely without exposing full physical address or sensitive PII."""
    status_map = {
        "pending": "⏳ Pendiente",
        "confirmed": "✅ Confirmado",
        "scheduled": "🗓️ Programado para fecha posterior",
        "assigned": "📋 Asignado a Chofer",
        "in_route": "🚚 En ruta / camino a tu domicilio",
        "delivered": "📦 Entregado",
        "cancelled": "❌ Cancelado",
        "rejected_by_driver": "⚠️ Reasignando unidad de reparto",
    }
    status_str = status_map.get(order.status, order.status)
    lines = [
        f"📋 **Pedido #{order.id}**",
        f"• **Estado:** {status_str}",
        f"• **Horario programado:** {order.delivery_schedule}",
    ]
    if order.driver_name and order.status in ("assigned", "in_route"):
        lines.append(f"• **Chofer asignado:** {order.driver_name}")

    if order.items:
        lines.append("• **Productos:**")
        for it in order.items:
            lines.append(f"  - {it.quantity}x {it.product_name} (${it.unit_price:.2f} c/u)")

    lines.append(f"• **Total:** ${order.total_amount:.2f} {order.currency}")
    return "\n".join(lines)


@tool
def get_order_status(
    order_id: int | None = None,
    phone: str = "",
    config: RunnableConfig = None,
) -> str:
    """Check the status and details of an existing customer order.

    Use this tool when a customer asks about their order status (e.g. "¿Cómo va mi pedido?",
    "Quiero rastrear mi folio 5", "Revisar pedido con mi teléfono").

    Args:
        order_id: Numeric Order ID / Folio (e.g. 1, 2, 5).
        phone: Customer phone number to search for recent orders.
    """
    configurable = config.get("configurable", {}) if config else {}
    tenant_id = configurable.get("tenant_id", "petroil")
    channel = configurable.get("channel", "telegram")
    channel_user_id = str(configurable.get("channel_user_id", ""))
    repo = get_repository()

    # 1. Detectar si el usuario intenta consultar múltiples números a la vez
    if phone and (len(re.findall(r"\b\d{7,12}\b", phone)) > 1 or any(sep in phone for sep in [",", ";", " y ", " and "])):
        return (
            "⛔ ACCESO DENEGADO: Por políticas de privacidad y seguridad, no puedes consultar información de múltiples números de teléfono. "
            "Informa cordialmente al usuario que no puedes procesar consultas de números ajenos ni acceder arbitrariamente a datos, "
            "y recuérdale tus funciones de atención al cliente (Realizar pedido, Consultar su propio pedido o Cancelar)."
        )

    # 2. Control de Acceso: Verificar si el usuario ya está vinculado a un teléfono en su canal
    if channel and channel_user_id and channel_user_id not in ("admin_manual", "dashboard", "cli_user"):
        bound_customer = repo.get_customer(tenant_id, channel, channel_user_id)
        if bound_customer and bound_customer.phone:
            clean_bound = re.sub(r"\D", "", bound_customer.phone)
            if phone:
                clean_query = re.sub(r"\D", "", phone)
                clean_q_10 = clean_query[-10:] if len(clean_query) >= 10 else clean_query
                clean_b_10 = clean_bound[-10:] if len(clean_bound) >= 10 else clean_bound
                if clean_query and len(clean_query) >= 7 and clean_q_10 != clean_b_10:
                    return (
                        "⛔ ACCESO DENEGADO: Por políticas de privacidad y seguridad, no tienes autorización para consultar pedidos de otros números telefónicos. "
                        "Informa cordialmente al usuario que solo puedes consultar pedidos de su propia cuenta vinculada."
                    )

    search_phone = phone
    if not order_id and not search_phone and channel and channel_user_id:
        bound_customer = repo.get_customer(tenant_id, channel, channel_user_id)
        if bound_customer and bound_customer.phone:
            search_phone = bound_customer.phone
        elif len(re.sub(r"\D", "", channel_user_id)) >= 10:
            search_phone = re.sub(r"\D", "", channel_user_id)[-10:]

    if order_id:
        try:
            order = repo.get_order_by_id(tenant_id, int(order_id))
            if not order:
                return f"No se encontró ningún pedido con el folio #{order_id}."

            # Verificar si el pedido pertenece al usuario en sesión
            if channel and channel_user_id and channel_user_id not in ("admin_manual", "dashboard", "cli_user"):
                bound_customer = repo.get_customer(tenant_id, channel, channel_user_id)
                clean_bound = re.sub(r"\D", "", bound_customer.phone) if (bound_customer and bound_customer.phone) else ""
                if not clean_bound and len(re.sub(r"\D", "", channel_user_id)) >= 10:
                    clean_bound = re.sub(r"\D", "", channel_user_id)[-10:]

                clean_order_phone = re.sub(r"\D", "", order.customer_phone or "")
                if clean_order_phone and clean_bound and clean_order_phone[-10:] != clean_bound[-10:]:
                    return f"No se encontró ningún pedido con el folio #{order_id} asociado a tu cuenta."

            return f"Información de tu pedido #{order_id}:\n\n{_to_safe_order_display(order)}"
        except Exception as e:
            return f"Error al buscar el pedido #{order_id}: {e}"

    if search_phone:
        orders = repo.get_orders_by_customer_phone(tenant_id, search_phone)
        if not orders:
            return f"No se encontraron pedidos registrados con el teléfono proporcionado ({search_phone})."

        res = [f"Se encontraron {len(orders)} pedido(s) en tu historial:\n"]
        for o in orders:
            res.append(_to_safe_order_display(o))
            res.append("-" * 30)
        return "\n".join(res)

    return "Por favor proporciona el número de folio de tu pedido para consultar su estatus."
