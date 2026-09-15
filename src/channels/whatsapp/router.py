"""WhatsApp Webhook Router (FastAPI).

Receives webhook verification requests and incoming messages from Meta WhatsApp Cloud API,
delegating conversation flow to the LangGraph sales agent without duplicating business logic.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import PlainTextResponse
from langchain_core.messages import HumanMessage

from src.channels.whatsapp.adapter import WhatsAppAdapter
from src.config.settings import get_settings
from src.graphs.sales_graph import compile_sales_graph
from src.repositories import get_repository
from src.repositories.sqlite_repo import get_db_connection
from src.services.geocoding import resolve_gps_address_to_name, reverse_geocode

logger = logging.getLogger(__name__)

router = APIRouter()
adapter = WhatsAppAdapter()
graph = compile_sales_graph()

TENANT_ID = "petroil"


# Carrito de compras interactivo temporal por usuario de WhatsApp (wa_id -> {prod_id: quantity})
wa_carts: dict[str, dict[str, int]] = {}


def get_user_cart(wa_id: str) -> dict[str, int]:
    """Obtiene el carrito activo del usuario."""
    return wa_carts.setdefault(wa_id, {})


def add_to_cart(wa_id: str, prod_id: str, qty: int = 1) -> dict[str, int]:
    """Agrega o incrementa la cantidad de un producto en el carrito del usuario."""
    cart = get_user_cart(wa_id)
    cart[prod_id] = cart.get(prod_id, 0) + qty
    return cart


def clear_cart(wa_id: str) -> None:
    """Vacía el carrito del usuario."""
    wa_carts[wa_id] = {}


def format_cart_summary(cart: dict[str, int], tenant_id: str = "petroil") -> tuple[str, float, int]:
    """Genera el resumen legible del carrito con totales y subtotales."""
    repo = get_repository()
    prods = repo.get_all_products(tenant_id)
    prods_by_id = {p.id: p for p in prods}

    lines = []
    total_price = 0.0
    total_qty = 0

    for pid, qty in cart.items():
        if qty > 0:
            prod = prods_by_id.get(pid)
            name = prod.name if prod else f"Cilindro ({pid})"
            price = prod.price if prod else 0.0
            subtotal = qty * price
            total_price += subtotal
            total_qty += qty
            lines.append(f"• *{qty}x {name}* — ${subtotal:,.2f} MXN")

    plural = "s" if total_qty > 1 else ""
    summary_text = (
        "🛒 *Tu selección actual:*\n"
        + "\n".join(lines)
        + f"\n\n💰 *Total acumulado:* ${total_price:,.2f} MXN ({total_qty} cilindro{plural})"
    )
    return summary_text, total_price, total_qty


@router.get("", response_class=PlainTextResponse)
@router.get("/", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    """WhatsApp Cloud API Webhook verification endpoint (Meta Challenge)."""
    settings = get_settings()
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    expected_token = settings.whatsapp_verify_token or "petroil_gas_webhook_secret"

    if mode == "subscribe" and token == expected_token:
        logger.info("[WhatsApp] Webhook successfully verified with Meta.")
        return challenge or ""

    logger.warning(f"[WhatsApp] Verification failed. Received token: {token}")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("")
@router.post("/")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receive real-time incoming messages and events from WhatsApp Cloud API."""
    try:
        payload = await request.json()
    except Exception:
        return {"status": "error", "detail": "Invalid JSON"}

    events = adapter.parse_webhook_events(payload, default_tenant_id=TENANT_ID)
    if not events:
        return {"status": "ok", "message": "No actionable user events"}

    for ev in events:
        background_tasks.add_task(process_whatsapp_event, ev)

    return {"status": "ok", "events_queued": len(events)}


async def process_whatsapp_event(event: dict[str, Any]) -> None:
    """Process a single incoming WhatsApp event asynchronously."""
    wa_id = event["wa_id"]
    if not wa_id:
        return

    msg_id = event.get("msg_id", "")
    if msg_id:
        await adapter.mark_as_read(msg_id)

    phone_10 = WhatsAppAdapter.extract_10_digit_phone(wa_id)
    thread_id = f"whatsapp:{TENANT_ID}:{wa_id}"
    repo = get_repository()

    config = {
        "configurable": {
            "thread_id": thread_id,
            "tenant_id": TENANT_ID,
            "channel": "whatsapp",
            "channel_user_id": wa_id,
        }
    }

    # -------------------------------------------------------------------------
    # 1. Manejo de Calificación / Encuestas de Entrega
    # -------------------------------------------------------------------------
    interactive_id = event.get("interactive_id") or ""
    if interactive_id.startswith("rate_driver:"):
        parts = interactive_id.split(":")
        order_id = int(parts[1])
        stars = max(1, min(5, int(parts[2])))

        order = repo.get_order_by_id(TENANT_ID, order_id)
        if order:
            repo.save_order_rating(
                tenant_id=TENANT_ID,
                order_id=order_id,
                driver_id=order.driver_id,
                customer_id=order.customer_id,
                rating=stars,
            )

            driver_name = "tu repartidor"
            if order.driver_id:
                d = repo.get_driver(order.driver_id)
                if d:
                    driver_name = d.name

            stars_str = "⭐" * stars
            if stars >= 4:
                body_msg = (
                    f"🌟 *¡Muchas gracias por calificar con {stars_str}!* ({stars}/5)\n\n"
                    f"¿Qué fue lo que más te agradó del servicio de {driver_name}?"
                )
                sections = [{
                    "title": "Aspectos Destacados",
                    "rows": [
                        {"id": f"rate_tag:{order_id}:Rapidez", "title": "⚡ Rapidez y puntualidad"},
                        {"id": f"rate_tag:{order_id}:Amabilidad", "title": "😊 Trato amable"},
                        {"id": f"rate_tag:{order_id}:Seguridad", "title": "🛡️ Cuidado y seguridad"},
                        {"id": f"rate_tag:{order_id}:Impecable", "title": "✨ Servicio impecable"},
                    ]
                }]
            else:
                body_msg = (
                    f"🙏 *Agradecemos tu calificación de {stars_str}* ({stars}/5)\n\n"
                    f"Lamentamos que tu experiencia con {driver_name} no haya sido óptima.\n"
                    "¿En qué aspecto podemos mejorar?"
                )
                sections = [{
                    "title": "Aspectos a Mejorar",
                    "rows": [
                        {"id": f"rate_tag:{order_id}:Demora", "title": "⏳ Demora en la entrega"},
                        {"id": f"rate_tag:{order_id}:Actitud", "title": "🙁 Actitud del chofer"},
                        {"id": f"rate_tag:{order_id}:Cilindro", "title": "📦 Problema con cilindro"},
                        {"id": f"rate_tag:{order_id}:Cobro", "title": "💵 Cobro o cambio"},
                    ]
                }]

            await adapter.send_interactive_list(
                recipient_wa_id=wa_id,
                body_text=body_msg,
                button_label="Seleccionar Detalle",
                sections=sections,
            )
            return

    if interactive_id.startswith("rate_tag:"):
        parts = interactive_id.split(":")
        order_id = int(parts[1])
        tag = parts[2]

        tag_labels = {
            "Rapidez": "⚡ Rapidez y puntualidad",
            "Amabilidad": "😊 Trato amable y cordial",
            "Seguridad": "🛡️ Cuidado y manejo seguro",
            "Impecable": "✨ Servicio impecable",
            "Demora": "⏳ Demora o tiempo de espera",
            "Actitud": "🙁 Actitud o atención del chofer",
            "Cilindro": "📦 Estado del cilindro",
            "Cobro": "💵 Inconveniente con el cobro/cambio",
        }
        tag_display = tag_labels.get(tag, tag)
        repo.update_order_rating_feedback(TENANT_ID, order_id, feedback_tag=tag_display)

        rating_data = repo.get_order_rating(TENANT_ID, order_id)
        stars_val = rating_data.get("rating", 5) if rating_data else 5
        stars_str = "⭐" * stars_val

        msg_final = (
            f"✅ *¡ENCUESTA COMPLETADA CON ÉXITO!*\n\n"
            f"⭐ *Calificación:* {stars_str} ({stars_val}/5)\n"
            f"💬 *Aspecto registrado:* {tag_display}\n\n"
            "¡Muchas gracias por tu tiempo y valiosa opinión! Nos ayuda a premiar a nuestros mejores choferes y mejorar día a día. ¡Estamos a tus órdenes! ⛽🌟"
        )
        await adapter.send_text_message(wa_id, msg_final)
        return

    # Soporte para calificación enviada como texto plano (ej. '5', '4', 'Excelente', '⭐⭐⭐⭐⭐')
    raw_text_rating = (event.get("text") or "").strip().lower()
    if not interactive_id and raw_text_rating:
        parsed_stars = None
        if raw_text_rating in ("5", "5 estrellas", "⭐ 5", "⭐⭐⭐⭐⭐", "excelente", "cinco"):
            parsed_stars = 5
        elif raw_text_rating in ("4", "4 estrellas", "⭐ 4", "⭐⭐⭐⭐", "bueno", "cuatro"):
            parsed_stars = 4
        elif raw_text_rating in ("3", "3 estrellas", "⭐ 3", "⭐⭐⭐", "regular", "tres"):
            parsed_stars = 3
        elif raw_text_rating in ("2", "2 estrellas", "⭐ 2", "⭐⭐", "malo", "dos"):
            parsed_stars = 2
        elif raw_text_rating in ("1", "1 estrella", "⭐ 1", "⭐", "muy malo", "uno"):
            parsed_stars = 1

        if parsed_stars is not None:
            # Buscar último pedido entregado para este cliente
            delivered_orders = []
            if phone_10:
                delivered_orders = [o for o in repo.get_orders_by_customer_phone(TENANT_ID, phone_10) if o.status == "delivered"]
            if not delivered_orders:
                cust = repo.get_customer(TENANT_ID, "whatsapp", wa_id)
                if cust:
                    delivered_orders = [o for o in repo.get_orders_by_customer(TENANT_ID, cust.id) if o.status == "delivered"]

            if delivered_orders:
                last_delivered = delivered_orders[0]
                existing_r = repo.get_order_rating(TENANT_ID, last_delivered.id)
                # Si no está calificado o se califica por primera vez
                if not existing_r or not existing_r.get("rating"):
                    repo.save_order_rating(
                        tenant_id=TENANT_ID,
                        order_id=last_delivered.id,
                        driver_id=last_delivered.driver_id,
                        customer_id=last_delivered.customer_id,
                        rating=parsed_stars,
                    )
                    driver_name = "tu repartidor"
                    if last_delivered.driver_id:
                        d = repo.get_driver(last_delivered.driver_id)
                        if d:
                            driver_name = d.name

                    stars_str = "⭐" * parsed_stars
                    if parsed_stars >= 4:
                        body_msg = (
                            f"🌟 *¡Muchas gracias por calificar con {stars_str}!* ({parsed_stars}/5)\n\n"
                            f"¿Qué fue lo que más te agradó del servicio de {driver_name}?"
                        )
                        sections = [{
                            "title": "Aspectos Destacados",
                            "rows": [
                                {"id": f"rate_tag:{last_delivered.id}:Rapidez", "title": "⚡ Rapidez y puntualidad"},
                                {"id": f"rate_tag:{last_delivered.id}:Amabilidad", "title": "😊 Trato amable"},
                                {"id": f"rate_tag:{last_delivered.id}:Seguridad", "title": "🛡️ Cuidado y seguridad"},
                                {"id": f"rate_tag:{last_delivered.id}:Impecable", "title": "✨ Servicio impecable"},
                            ]
                        }]
                    else:
                        body_msg = (
                            f"🙏 *Agradecemos tu calificación de {stars_str}* ({parsed_stars}/5)\n\n"
                            f"Lamentamos que tu experiencia con {driver_name} no haya sido óptima.\n"
                            "¿En qué aspecto podemos mejorar?"
                        )
                        sections = [{
                            "title": "Aspectos a Mejorar",
                            "rows": [
                                {"id": f"rate_tag:{last_delivered.id}:Demora", "title": "⏳ Demora en la entrega"},
                                {"id": f"rate_tag:{last_delivered.id}:Actitud", "title": "🙁 Actitud del chofer"},
                                {"id": f"rate_tag:{last_delivered.id}:Cilindro", "title": "📦 Problema con cilindro"},
                                {"id": f"rate_tag:{last_delivered.id}:Cobro", "title": "💵 Cobro o cambio"},
                            ]
                        }]

                    await adapter.send_interactive_list(
                        recipient_wa_id=wa_id,
                        body_text=body_msg,
                        button_label="Seleccionar Detalle",
                        sections=sections,
                    )
                    return

    # -------------------------------------------------------------------------
    # 2. Manejo de Ubicación GPS
    # -------------------------------------------------------------------------
    loc = event.get("location")
    if loc and loc.get("latitude") is not None and loc.get("longitude") is not None:
        lat = float(loc["latitude"])
        lng = float(loc["longitude"])
        direccion_detectada = reverse_geocode(lat, lng)

        prompt_gps = (
            f"📍 [UBICACIÓN GPS EN TIEMPO REAL COMPARTIDA POR EL CLIENTE VÍA WHATSAPP]\n"
            f"- Dirección detectada en mapa: {direccion_detectada}\n"
            f"- Coordenadas GPS exactas: Latitud {lat:.6f}, Longitud {lng:.6f}\n\n"
            f"INSTRUCCIÓN PARA EL ASISTENTE:\n"
            f"1. Confirma al cliente que recibiste con éxito su ubicación en '{direccion_detectada}'.\n"
            f"2. Pregúntale amablemente si confirma esta ubicación como su punto de entrega y si tiene referencias adicionales (ej. color de casa o fachada).\n"
            f"3. Cuando llames a la herramienta create_order para finalizar el pedido, en el campo 'delivery_address' DEBES registrar el nombre de la calle/colonia ('{direccion_detectada}'), agregando cualquier referencia del cliente (ej. '{direccion_detectada} - Casa blanca'). NUNCA uses números de latitud ni longitud como nombre de dirección. Y DEBES pasar obligatoriamente: delivery_lat={lat:.6f}, delivery_lng={lng:.6f}."
        )

        await _invoke_graph_and_reply(
            user_text=prompt_gps,
            wa_id=wa_id,
            phone_10=phone_10,
            config=config,
        )
        return

    # -------------------------------------------------------------------------
    # 3. Mapeo de Acciones Interactivas de Botones y Listas
    # -------------------------------------------------------------------------
    texto_usuario = event.get("text", "").strip()

    if interactive_id:
        if interactive_id == "client_svc:cilindro":
            # Limpiar carrito previo y desplegar catálogo interactivo
            clear_cart(wa_id)
            sections = adapter.get_cylinder_catalog_list_sections(TENANT_ID)
            await adapter.send_interactive_list(
                recipient_wa_id=wa_id,
                body_text="🛒 *Catálogo de Cilindros de Gas LP*\nSelecciona la capacidad que necesitas en el menú a continuación:",
                button_label="Ver Opciones",
                sections=sections,
            )
            return

        elif interactive_id == "client_svc:estacionario":
            clear_cart(wa_id)
            texto_usuario = "Deseo pedir gas para tanque estacionario"

        elif interactive_id.startswith("cart_add:"):
            parts = interactive_id.split(":")
            prod_id = parts[1]
            qty = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
            cart = add_to_cart(wa_id, prod_id, qty)
            summary_text, total_price, total_qty = format_cart_summary(cart, TENANT_ID)

            plural = "s" if total_qty > 1 else ""
            body = (
                f"{summary_text}\n\n"
                f"¿Deseas agregar más cilindros a tu pedido o continuar con tu entrega?"
            )
            btn_checkout_title = f"✅ Continuar ({total_qty})" if len(f"✅ Continuar ({total_qty})") <= 20 else "✅ Continuar"
            buttons = [
                {"id": "cart_more", "title": "➕ Agregar Otro"},
                {"id": "cart_checkout", "title": btn_checkout_title},
                {"id": "cart_clear", "title": "🗑️ Vaciar"},
            ]
            await adapter.send_interactive_buttons(
                recipient_wa_id=wa_id,
                body_text=body,
                buttons=buttons,
            )
            return

        elif interactive_id == "cart_more":
            # Re-desplegar lista de catálogo mostrando el resumen actual
            cart = get_user_cart(wa_id)
            summary_text, _, total_qty = format_cart_summary(cart, TENANT_ID) if cart else ("", 0, 0)
            sections = adapter.get_cylinder_catalog_list_sections(TENANT_ID)
            body = (
                f"{summary_text}\n\nSelecciona el siguiente cilindro que deseas agregar a tu pedido:"
                if summary_text
                else "🛒 *Catálogo de Cilindros de Gas LP*\nSelecciona la capacidad que necesitas en el menú:"
            )
            await adapter.send_interactive_list(
                recipient_wa_id=wa_id,
                body_text=body,
                button_label="Agregar Cilindro",
                sections=sections,
            )
            return

        elif interactive_id == "cart_clear":
            clear_cart(wa_id)
            sections = adapter.get_cylinder_catalog_list_sections(TENANT_ID)
            await adapter.send_interactive_list(
                recipient_wa_id=wa_id,
                body_text="🗑️ *Carrito vaciado.*\n\nSelecciona los cilindros que necesitas en el menú a continuación:",
                button_label="Ver Catálogo",
                sections=sections,
            )
            return

        elif interactive_id == "cart_checkout":
            cart = get_user_cart(wa_id)
            if not cart or sum(cart.values()) == 0:
                sections = adapter.get_cylinder_catalog_list_sections(TENANT_ID)
                await adapter.send_interactive_list(
                    recipient_wa_id=wa_id,
                    body_text="🛒 *Tu carrito está vacío.*\nPor favor selecciona al menos un cilindro para continuar:",
                    button_label="Ver Opciones",
                    sections=sections,
                )
                return

            prods = repo.get_all_products(TENANT_ID)
            prods_by_id = {p.id: p for p in prods}
            items_str = ", ".join(
                f"{qty}x {prods_by_id[pid].name if pid in prods_by_id else pid}"
                for pid, qty in cart.items()
                if qty > 0
            )
            texto_usuario = f"Deseo ordenar los siguientes productos seleccionados de tu catálogo: {items_str}."
            clear_cart(wa_id)

        elif interactive_id == "client_pay:efectivo":
            texto_usuario = "Mi método de pago será en Efectivo"

        elif interactive_id == "client_pay:terminal":
            texto_usuario = "Mi método de pago será con Terminal (Tarjeta)"

        elif interactive_id == "client_confirm:yes":
            texto_usuario = "Sí, confirmar pedido"

        elif interactive_id == "client_confirm:edit":
            texto_usuario = "Deseo modificar los datos de mi pedido"

        elif interactive_id == "client_confirm:cancel":
            clear_cart(wa_id)
            texto_usuario = "No, deseo cancelar este pedido"

        elif interactive_id == "client_addr:del_menu":
            phone_to_search = phone_10
            cust = repo.get_customer_by_phone(TENANT_ID, phone_to_search) if phone_to_search else None
            if not cust:
                cust = repo.get_customer(TENANT_ID, "whatsapp", wa_id)

            addrs = cust.addresses if (cust and cust.addresses) else []
            if not addrs:
                await adapter.send_text_message(
                    wa_id,
                    "ℹ️ No se encontraron direcciones guardadas en tu cuenta para eliminar."
                )
                return

            sections = adapter.get_delete_addresses_list_sections(addrs)
            body = (
                "🗑️ *Eliminar Dirección Guardada*\n\n"
                "Selecciona en el menú a continuación la dirección que deseas borrar de tu cuenta permanente:"
            )
            await adapter.send_interactive_list(
                recipient_wa_id=wa_id,
                body_text=body,
                button_label="Eliminar Dirección",
                sections=sections,
            )
            return

        elif interactive_id.startswith("del_addr:"):
            addr_id_str = interactive_id.split(":", 1)[1]
            if addr_id_str.isdigit():
                addr_id = int(addr_id_str)
                cust = repo.get_customer_by_phone(TENANT_ID, phone_10) if phone_10 else None
                if not cust:
                    cust = repo.get_customer(TENANT_ID, "whatsapp", wa_id)

                customer_id = cust.id if cust else None
                addr_text_deleted = ""

                with get_db_connection() as conn:
                    row_addr = conn.execute("SELECT * FROM customer_addresses WHERE id = ?", (addr_id,)).fetchone()
                    if row_addr:
                        addr_text_deleted = row_addr["address"]
                        if not customer_id:
                            customer_id = row_addr["customer_id"]

                if customer_id:
                    repo.delete_customer_address(customer_id, addr_id)
                    remaining = repo.get_customer_addresses(customer_id)
                    addr_display = addr_text_deleted or f"#{addr_id}"

                    if remaining:
                        if len(remaining) == 1:
                            buttons = adapter.get_customer_addresses_buttons(remaining)
                            body = (
                                f"✅ *Dirección eliminada con éxito:*\n📍 `{addr_display}`\n\n"
                                "¿A cuál de tus direcciones restantes deseas que enviemos tu pedido o prefieres ingresar una nueva?"
                            )
                            await adapter.send_interactive_buttons(
                                recipient_wa_id=wa_id,
                                body_text=body,
                                buttons=buttons,
                            )
                        else:
                            sections = adapter.get_customer_addresses_list_sections(remaining)
                            body = (
                                f"✅ *Dirección eliminada con éxito:*\n📍 `{addr_display}`\n\n"
                                "¿A cuál de tus direcciones restantes deseas que enviemos tu pedido o prefieres ingresar una nueva?"
                            )
                            await adapter.send_interactive_list(
                                recipient_wa_id=wa_id,
                                body_text=body,
                                button_label="Ver Direcciones",
                                sections=sections,
                            )
                    else:
                        msg = (
                            f"✅ *Dirección eliminada con éxito:*\n📍 `{addr_display}`\n\n"
                            "Ya no tienes más direcciones guardadas en tu cuenta. Por favor escribe tu nueva dirección de entrega completa o comparte tu ubicación GPS 📍 para continuar con tu pedido:"
                        )
                        await adapter.send_text_message(wa_id, msg)
                    return
                else:
                    await adapter.send_text_message(
                        wa_id,
                        "⚠️ No se pudo localizar la dirección a eliminar. Por favor intenta nuevamente."
                    )
                    return

        elif interactive_id.startswith("client_addr:"):
            choice = interactive_id.split(":", 1)[1]
            if choice == "new":
                texto_usuario = "Deseo ingresar una nueva dirección de entrega"
            elif choice == "del_menu":
                # Fallback redundante si llega client_addr:del_menu
                pass
            else:
                raw_title = (event.get("interactive_title") or event.get("text") or "").strip()
                # Limpiar prefijos de numeración y emoji de pin
                clean_title = re.sub(r"^\d+[\.\)\-]+\s*(?:📍|\uD83D\uDCCD)?\s*", "", raw_title).strip()
                # Extraer texto limpio de la dirección
                clean_addr = re.sub(r"^\[.*?\]\s*", "", clean_title).strip()

                if clean_addr and len(clean_addr) > 2 and not clean_addr.lower().startswith("nueva direcci"):
                    texto_usuario = f"Deseo que envíen el pedido a la dirección #{choice}: {clean_addr}"
                elif clean_title and len(clean_title) > 2 and not clean_title.lower().startswith("nueva direcci"):
                    texto_usuario = f"Deseo que envíen el pedido a la dirección #{choice} ({clean_title})"
                else:
                    texto_usuario = f"Deseo que envíen el pedido a mi dirección registrada número {choice}"

    # -------------------------------------------------------------------------
    # 4. Invocación del Agente de Ventas con LangGraph
    # -------------------------------------------------------------------------
    if not texto_usuario:
        return

    await _invoke_graph_and_reply(
        user_text=texto_usuario,
        wa_id=wa_id,
        phone_10=phone_10,
        config=config,
    )


async def _invoke_graph_and_reply(
    user_text: str,
    wa_id: str,
    phone_10: str,
    config: dict[str, Any],
) -> None:
    """Invoke LangGraph agent and dispatch formatted WhatsApp response."""
    try:
        resultado = await graph.ainvoke(
            {
                "messages": [HumanMessage(content=user_text)],
                "channel": "whatsapp",
                "channel_user_id": wa_id,
            },
            config=config,
        )

        ai_message = resultado["messages"][-1]
        respuesta = ai_message.content
        if not isinstance(respuesta, str):
            respuesta = str(respuesta)

        # Detectar botones o listas interactivas contextuales
        cleaned_text, interactive_spec = adapter.detect_interactive_elements(
            respuesta=respuesta,
            phone=phone_10,
            channel_user_id=wa_id,
            tenant_id=TENANT_ID,
            user_text=user_text,
        )

        if interactive_spec:
            spec_type = interactive_spec.get("type")
            if spec_type == "buttons":
                await adapter.send_interactive_buttons(
                    recipient_wa_id=wa_id,
                    body_text=cleaned_text,
                    buttons=interactive_spec["buttons"],
                )
                return
            elif spec_type == "list":
                await adapter.send_interactive_list(
                    recipient_wa_id=wa_id,
                    body_text=cleaned_text,
                    button_label=interactive_spec.get("button_label", "Ver Opciones"),
                    sections=interactive_spec["sections"],
                )
                return

        # Mensaje de texto normal
        await adapter.send_text_message(recipient_wa_id=wa_id, text=respuesta)

    except Exception as e:
        logger.error(f"❌ Error al procesar mensaje de WhatsApp para {wa_id}: {e}", exc_info=True)
        await adapter.send_text_message(
            recipient_wa_id=wa_id,
            text="⚠️ Ocurrió un error al procesar tu solicitud. Por favor intenta de nuevo en unos momentos.",
        )
