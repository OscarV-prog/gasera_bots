"""Telegram Bot adapter for the LangGraph multi-tenant sales agent."""

import logging
import re
import sys
from datetime import datetime

# Forzar UTF-8 en terminal de Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from langchain_core.messages import HumanMessage
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

from src.config.settings import get_settings
from src.config.tenant_config import get_tenant
from src.database import init_db
from src.graphs.sales_graph import compile_sales_graph
from src.models.customer import CustomerAddress
from src.repositories import get_repository
from src.services.geocoding import resolve_gps_address_to_name, reverse_geocode
from src.services.notifications import notify_driver

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Configuración del tenant
TENANT_ID = "petroil"
tenant = get_tenant(TENANT_ID)
graph = compile_sales_graph()

# Token del bot de clientes
settings = get_settings()
TELEGRAM_BOT_TOKEN = settings.telegram_bot_token

# Inicializar base de datos SQLite
init_db()


def get_teclado_cliente() -> ReplyKeyboardMarkup:
    """Teclado de acceso rápido para el cliente."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📍 Compartir Mi Ubicación Actual", request_location=True)],
        ],
        resize_keyboard=True,
    )


def get_botones_tipo_servicio() -> InlineKeyboardMarkup:
    """Botones interactivos para elegir tipo de servicio al inicio."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🛻 Cilindro de Gas", callback_data="client_svc:cilindro"),
                InlineKeyboardButton("🚛 Tanque Estacionario", callback_data="client_svc:estacionario"),
            ]
        ]
    )


def get_catalogo_productos_db(tenant_id: str = "petroil") -> list:
    """Obtiene los productos activos en existencia directamente desde SQLite."""
    try:
        repo = get_repository()
        prods = repo.get_all_products(tenant_id)
        # Filtrar cilindros y productos de gas en existencia
        return [
            p for p in prods
            if getattr(p, "in_stock", True) and (
                (getattr(p, "category", "") or "").lower() in ("cilindros", "gas lp", "gas")
                or "cilindro" in p.name.lower()
                or "gas" in p.name.lower()
            )
        ]
    except Exception as e:
        logger.error(f"Error cargando catálogo desde BD: {e}")
        return []


def get_botones_productos_cilindros(carrito: dict[str, int] | None = None) -> InlineKeyboardMarkup:
    """Botones interactivos dinámicos generados desde la base de datos SQLite."""
    carrito = carrito or {}
    total_items = sum(carrito.values())
    prods = get_catalogo_productos_db()

    botones_fila = []
    filas = []

    for p in prods:
        m_kg = re.search(r"(\d+\s*kg)", p.name, re.IGNORECASE)
        label_size = m_kg.group(1).upper() if m_kg else p.name
        if len(label_size) > 16:
            label_size = label_size[:15] + ".."

        cant = carrito.get(p.id, 0)
        c_tag = f" ({cant})" if cant > 0 else ""

        btn_text = f"+ {label_size} (${p.price:.0f}){c_tag}"
        botones_fila.append(InlineKeyboardButton(btn_text, callback_data=f"cart_add:{p.id}"))

        if len(botones_fila) == 2:
            filas.append(botones_fila)
            botones_fila = []

    if botones_fila:
        filas.append(botones_fila)

    if total_items > 0:
        filas.append([
            InlineKeyboardButton("🗑️ Vaciar", callback_data="cart_clear"),
            InlineKeyboardButton(f"✅ Continuar ({total_items}) ➡️", callback_data="cart_checkout"),
        ])

    return InlineKeyboardMarkup(filas)


def texto_resumen_catalogo(carrito: dict[str, int] | None = None) -> str:
    """Genera el texto de catálogo con el resumen interactivo del carrito sin redundancias."""
    prods = get_catalogo_productos_db()

    if not carrito or sum(carrito.values()) == 0:
        return "🛒 **Selección de Cilindros:**\nSelecciona en los botones de abajo los cilindros que necesitas (o escribe tu pedido si lo prefieres):"

    lineas_carrito = []
    total_pesos = 0.0
    prods_by_id = {p.id: p for p in prods}

    for pid, cant in carrito.items():
        if cant > 0 and pid in prods_by_id:
            p = prods_by_id[pid]
            sub = cant * p.price
            total_pesos += sub
            lineas_carrito.append(f"• **{cant}x {p.name}** — ${sub:.2f} MXN")

    return (
        "🛒 **Tu selección actual:**\n" +
        "\n".join(lineas_carrito) + "\n" +
        f"💰 **Total acumulado:** ${total_pesos:.2f} MXN\n\n" +
        "Puedes tocar más botones para agregar más piezas o presionar **'✅ Continuar'** para seguir con tu pedido."
    )


def get_botones_direcciones_cliente(addresses: list[CustomerAddress]) -> InlineKeyboardMarkup:
    """Genera botones interactivos para cada dirección guardada del cliente + opción de nueva dirección y eliminar."""
    botones = []
    for i, addr in enumerate(addresses, 1):
        addr_text = resolve_gps_address_to_name(addr.address.strip())
        alias_tag = f"[{addr.alias}] " if addr.alias and addr.alias not in ("Principal", f"Dirección {i}") else ""
        short_addr = f"{i}. 📍 {alias_tag}{addr_text}"
        if len(short_addr) > 42:
            short_addr = short_addr[:39] + "..."
        botones.append([InlineKeyboardButton(short_addr, callback_data=f"client_addr:{i}")])

    botones.append([InlineKeyboardButton("➕ Ingresar nueva dirección", callback_data="client_addr:new")])
    if addresses:
        botones.append([InlineKeyboardButton("🗑️ Eliminar una dirección", callback_data="client_addr_del_menu")])
    return InlineKeyboardMarkup(botones)


def get_botones_eliminar_direcciones(addresses: list[CustomerAddress]) -> InlineKeyboardMarkup:
    """Genera botones para seleccionar cuál dirección eliminar de la cuenta."""
    botones = []
    for i, addr in enumerate(addresses, 1):
        addr_text = resolve_gps_address_to_name(addr.address.strip())
        alias_tag = f"[{addr.alias}] " if addr.alias and addr.alias not in ("Principal", f"Dirección {i}") else ""
        short_addr = f"🗑️ {i}. {alias_tag}{addr_text}"
        if len(short_addr) > 42:
            short_addr = short_addr[:39] + "..."
        botones.append([InlineKeyboardButton(short_addr, callback_data=f"client_addr_del:{addr.id}:{i}")])

    botones.append([InlineKeyboardButton("🔙 Volver a selección de dirección", callback_data="client_addr_back")])
    return InlineKeyboardMarkup(botones)


def get_botones_metodo_pago() -> InlineKeyboardMarkup:
    """Botones interactivos para seleccionar método de pago."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💵 Efectivo", callback_data="client_pay:efectivo"),
                InlineKeyboardButton("💳 Terminal (Tarjeta)", callback_data="client_pay:terminal"),
            ]
        ]
    )


def get_botones_resumen_confirmacion() -> InlineKeyboardMarkup:
    """Botones interactivos para confirmar, editar o cancelar el pedido en el resumen."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Sí, Confirmar Pedido", callback_data="client_confirm:yes"),
            ],
            [
                InlineKeyboardButton("✏️ Modificar Datos", callback_data="client_confirm:edit"),
                InlineKeyboardButton("❌ Cancelar", callback_data="client_confirm:cancel"),
            ],
        ]
    )


def detectar_botones_mensaje(respuesta: str, phone: str = "", channel_user_id: str = "") -> InlineKeyboardMarkup | None:
    """Detecta si la respuesta del asistente debe llevar botones contextuales."""
    resp_lower = respuesta.lower()

    # 1. ¿Es un pedido ya creado/confirmado en BD o consulta de historial/estatus? -> GUARD ESTRICTO: NINGÚN BOTÓN
    is_confirmed_order_or_history = any(k in resp_lower for k in [
        "pedido confirmado", "pedido ha sido registrado", "registrado con el folio",
        "pedido registrado", "creado exitosamente", "asignado a chofer",
        "registrado exitosamente", "registrada exitosamente",
        "nuestro repartidor se comunicará", "nuestro repartidor se comunicara",
        "gracias por tu preferencia", "¡gracias por tu preferencia!", "gracias por confiar",
        "historial de tus pedidos", "encontré", "encontre", "pedidos en tu historial",
        "información de tu pedido", "informacion de tu pedido", "estatus de tu pedido",
        "se encontraron", "tus pedidos registrados", "detalles de tu pedido"
    ]) or (
        "pedido #" in resp_lower and any(k in resp_lower for k in ["estado:", "confirmado", "entregado", "en ruta", "cancelado"])
        and not any(k in resp_lower for k in ["¿deseas confirmar", "¿confirmamos", "resumen de tu pedido"])
    )
    if is_confirmed_order_or_history:
        return None

    # Detectar si el mensaje es una explicación general del servicio, bienvenida o mensaje de seguridad/límites
    es_explicacion_general_o_seguridad = any(k in resp_lower for k in [
        "con gusto te explico", "mi servicio", "mi función", "soy el asistente",
        "asistente virtual", "puedo ayudarte con", "el proceso de pedido es",
        "te pregunto qué necesitas", "no puedo decodificar", "no tengo capacidad ni autorización",
        "únicamente de atención", "payload", "atención al cliente", "asistente de **gas a tu puerta",
        "¿te gustaría hacer un pedido", "¿te gustaría que te ayude con tu pedido",
        "¿te gustaría realizar un pedido", "¿deseas hacer un pedido", "bienvenido a gas a tu puerta"
    ])

    # 2. ¿Es el resumen del pedido esperando confirmación del cliente? (PASO 6)
    if not es_explicacion_general_o_seguridad and (
        any(k in resp_lower for k in [
            "resumen de tu pedido", "datos de tu pedido", "detalles de tu pedido", "información de tu pedido",
            "tu pedido sería", "tu pedido es:", "resumen completo"
        ])
        and any(k in resp_lower for k in [
            "confirmar", "confírmame", "confirmame", "correctos", "proceder", "procesar",
            "procedo", "de acuerdo", "¿está todo bien", "¿esta todo bien"
        ])
        and ("total:" in resp_lower or "$" in resp_lower)
    ):
        return get_botones_resumen_confirmacion()

    # 3. ¿Es pregunta específica sobre cómo pagará el cliente? (PASO 5: Efectivo o Terminal)
    es_pregunta_pago = not es_explicacion_general_o_seguridad and (
        any(k in resp_lower for k in [
            "en efectivo o con terminal", "en efectivo o terminal", "efectivo o tarjeta",
            "efectivo o con tarjeta", "pagarás en efectivo", "pagaras en efectivo",
            "cómo deseas pagar", "como deseas pagar", "cómo te gustaría pagar", "como te gustaria pagar",
            "cómo prefieres pagar", "como prefieres pagar",
            "cómo prefieres realizar el pago", "como prefieres realizar el pago",
            "cómo deseas realizar el pago", "como deseas realizar el pago",
            "deseas realizar el pago", "prefieres realizar el pago",
            "realizar el pago", "realizarás el pago", "realizaras el pago",
            "deseas pagar en efectivo", "cuál será tu forma de pago", "cual sera tu forma de pago",
            "forma de pago será", "forma de pago sera", "cuál eliges", "cual eliges"
        ])
        or (
            ("pago" in resp_lower or "pagar" in resp_lower)
            and any(k in resp_lower for k in [
                "efectivo", "terminal", "tarjeta", "cómo", "como", "cuál", "cual",
                "prefieres", "deseas", "método", "metodo", "forma", "opciones", "medio", "eliges"
            ])
            and not any(k in resp_lower for k in ["te pregunto", "proceso", "guiado", "siguiente paso"])
        )
    )
    if es_pregunta_pago:
        return get_botones_metodo_pago()

    # 4. GUARD ESTRICTO DE HORARIO/FECHA O ESCRITURA DE NUEVA DIRECCIÓN (PASO 4) -> NINGÚN BOTÓN
    es_solicitud_escritura_nueva_direccion = (
        any(k in resp_lower for k in [
            "indícame tu nueva dirección", "indicame tu nueva direccion",
            "indícame la nueva dirección", "indicame la nueva direccion",
            "indícame una nueva dirección", "indicame una nueva direccion",
            "indicarme una nueva dirección", "indicarmela una nueva direccion",
            "proporciona los datos de tu nueva dirección", "proporciona los datos de tu nueva direccion",
            "proporciona tu nueva dirección", "proporciona tu nueva direccion",
            "proporcióname tu nueva dirección", "proporcioname tu nueva direccion",
            "proporcióname los datos de tu nueva dirección", "proporcioname los datos de tu nueva direccion",
            "escribe tu nueva dirección", "escribe tu nueva direccion",
            "escribe tu dirección", "escribe tu direccion",
            "ingresa tu nueva dirección", "ingresa tu nueva direccion",
            "ingresa tu dirección", "ingresa tu direccion",
            "compárteme tu nueva dirección", "comparteme tu nueva direccion",
            "compárteme tu dirección", "comparteme tu direccion",
            "comparte tu nueva dirección", "comparte tu nueva direccion",
            "comparte tu ubicación o escribe", "comparte tu ubicacion o escribe",
            "calle, número", "calle, numero", "calle y número", "calle y numero",
            "colonia y referencias", "número exterior", "numero exterior",
            "indícame la dirección completa", "indicame la direccion completa",
            "indícame tu dirección completa", "indicame tu direccion completa",
            "cuál es tu dirección completa", "cual es tu direccion completa",
            "por favor compárteme tu ubicación", "por favor comparteme tu ubicacion",
            "por favor indícame la calle", "por favor indicame la calle",
            "para registrarla en tu pedido", "para registrarla en el sistema",
            "cuál es la nueva dirección", "cual es la nueva direccion"
        ])
        and not any(k in resp_lower for k in [
            "botones interactivos", "seleccionar tu dirección", "seleccionar tu direccion",
            "selecciona tu dirección", "selecciona tu direccion", "a cuál de tus direcciones", "cual de tus direcciones"
        ])
    )

    if not es_explicacion_general_o_seguridad and (
        any(k in resp_lower for k in [
            "qué día", "que dia", "¿qué día", "¿que dia",
            "recibir tu pedido", "cuándo deseas", "cuando deseas", "cuándo te gustaría", "cuando te gustaria",
            "fecha de entrega", "programar tu entrega", "a qué hora", "a que hora", "cuándo requieres", "cuando requieres"
        ])
        or es_solicitud_escritura_nueva_direccion
    ):
        return None

    # 5. ¿Es selección de DIRECCIÓN para cliente (PASO 3)?
    # NOTA: Se generan botones para que las direcciones salgan en botones y optimizar_respuesta_con_botones limpia el texto
    es_pregunta_direccion = not es_explicacion_general_o_seguridad and not es_solicitud_escritura_nueva_direccion and any(k in resp_lower for k in [
        "dirección registrada", "direccion registrada", "direcciones registradas",
        "direcciones guardadas", "dirección guardada", "direccion guardada",
        "domicilio registrado", "domicilios registrados", "domicilio guardado", "domicilios guardados",
        "siguientes direcciones", "direcciones para ti",
        "seleccionar tu dirección", "seleccionar tu direccion",
        "selecciona tu dirección", "selecciona tu direccion",
        "seleccionar dirección", "seleccionar direccion",
        "selecciona dirección", "selecciona direccion",
        "seleccionar tu domicilio", "seleccionar domicilio", "selecciona tu domicilio",
        "botones interactivos", "botones interactivos de la pantalla", "botones de la pantalla",
        "a cuál de tus direcciones", "cual de tus direcciones",
        "a cuál de estas direcciones", "cual de estas direcciones",
        "a cuál de ellas", "a cual de ellas",
        "a cuál de esas direcciones", "a cual de esas direcciones",
        "misma dirección", "misma direccion",
        "deseas que entreguemos en", "deseas que enviemos a",
        "deseas que te lo enviemos a", "deseas que te la enviemos a",
        "deseas recibir tu pedido en", "deseas recibirlo en",
        "prefieres proporcionar una nueva dirección", "prefieres proporcionar una nueva direccion",
        "ingresar una nueva dirección", "ingresar una nueva direccion",
        "proporcionar una nueva dirección", "proporcionar una nueva direccion",
        "cuál de tus domicilios", "cual de tus domicilios",
        "en cuál de tus direcciones", "en cual de tus direcciones",
        "cliente frecuente",
    ])
    if es_pregunta_direccion:
        repo = get_repository()
        cust = None
        if phone:
            cust = repo.get_customer_by_phone(TENANT_ID, phone)
        if not cust and channel_user_id:
            cust = repo.get_customer(TENANT_ID, "telegram", str(channel_user_id))
        if not cust:
            match_resp_phone = re.search(r"\b(\d{10})\b", respuesta)
            if match_resp_phone:
                cust = repo.get_customer_by_phone(TENANT_ID, match_resp_phone.group(1))

        addrs: list[CustomerAddress] = []
        if cust and not addrs:
            if cust.addresses:
                addrs = list(cust.addresses)
            elif cust.address:
                addrs = [CustomerAddress(id=1, address=cust.address, alias="Principal")]

        # Si no se obtuvieron de la BD directamente, extraer las direcciones numeradas del propio mensaje
        if not addrs:
            matches = re.findall(
                r"^\s*(\d+)\.\s*(?:📍|\uD83D\uDCCD)?\s*(?:\*\*\[(.*?)\]\*\*)?\s*(.+)$",
                respuesta,
                re.M,
            )
            for m in matches:
                idx = int(m[0])
                alias = m[1].strip() if m[1] else f"Dirección {idx}"
                addr_text = m[2].strip()
                if addr_text and not addr_text.endswith("?"):
                    addrs.append(CustomerAddress(id=idx, address=addr_text, alias=alias))

        if addrs:
            return get_botones_direcciones_cliente(addrs)
        return None

    # 6. GUARD ESTRICTO DE TELÉFONO (PASO 2: solicitando teléfono para buscar cuenta) -> NINGÚN BOTÓN
    # Si el bot está pidiendo el número de teléfono, NUNCA deben salir botones para permitir teclear el número
    if not es_explicacion_general_o_seguridad and any(k in resp_lower for k in [
        "teléfono", "telefono", "celular", "proporcionarme tu número", "proporcionarme tu numero",
        "cuál es tu número", "cual es tu numero", "buscar tu cuenta", "para buscar tu cuenta",
        "número de teléfono", "numero de telefono", "número celular", "numero celular",
        "necesito tu número", "necesito tu numero", "proporcionas tu número", "proporcionas tu numero",
        "número a 10 dígitos", "numero a 10 digitos"
    ]):
        return None

    # 7. ¿Es catálogo de cilindros / selección de capacidad (PASO 1)?
    # Solo si el asistente está preguntando u ofreciendo qué capacidad o tamaño de cilindro desea y NO estamos en pasos posteriores
    es_tema_cilindro = any(k in resp_lower for k in ["cilindro", "cilindros"]) or any(k in resp_lower for k in ["5 kg", "10 kg", "20 kg", "30 kg", "45 kg"])
    es_pregunta_catalogo = not es_explicacion_general_o_seguridad and not es_pregunta_pago and not es_pregunta_direccion and (
        any(k in resp_lower for k in [
            "qué capacidad", "que capacidad", "cuántos kilos", "cuantos kilos",
            "qué tamaño", "que tamaño", "de qué capacidad", "de que capacidad",
            "de cuántos kilos", "de cuantos kilos", "de que tamaño", "de qué tamaño",
            "cuántos cilindros", "cuantos cilindros", "cuál cilindro", "cual cilindro",
            "opciones de cilindros", "capacidades disponibles", "precios de cilindros",
            "catálogo de cilindros", "catalogo de cilindros", "seleccionar en los botones",
            "opciones disponibles"
        ]) or (
            ("cilindro" in resp_lower or "cilindros" in resp_lower)
            and any(k in resp_lower for k in [
                "opciones", "disponibles", "disponible", "precios", "precio", "costo",
                "catálogo", "catalogo", "cuál", "cual", "cuántos", "cuantos", "necesitas", "deseas", "tamaño"
            ])
            and not any(k in resp_lower for k in ["estacionario", "tanque estacionario", "pago", "pagar", "efectivo", "terminal", "tarjeta", "dirección", "direccion", "horario", "hora"])
        )
    )

    if es_tema_cilindro and es_pregunta_catalogo:
        return get_botones_productos_cilindros()

    # 8. Botones de tipo de servicio [🛻 Cilindro de Gas] y [🚛 Tanque Estacionario]
    # SOLO se muestran al inicio, bienvenida o cuando se pregunta explícitamente qué tipo de servicio/pedido desea.
    es_inicio_o_tipo_servicio = (
        es_explicacion_general_o_seguridad
        or any(k in resp_lower for k in [
            "bienvenido", "bienvenida",
            "cilindro o tanque estacionario", "cilindro o estacionario", "tanque estacionario o cilindro",
            "qué servicio necesitas", "que servicio necesitas", "¿qué servicio", "¿que servicio",
            "qué tipo de servicio", "que tipo de servicio",
            "en qué podemos ayudarte", "en que podemos ayudarte",
            "en qué te podemos ayudar", "en que te podemos ayudar",
            "en qué te puedo ayudar", "en que te puedo ayudar",
            "¿te gustaría hacer un pedido", "¿te gustaría realizar un pedido", "¿deseas hacer un pedido",
            "¿te gustaría que te ayude con tu pedido", "en qué te asisto"
        ])
    )
    if es_inicio_o_tipo_servicio:
        return get_botones_tipo_servicio()

    # Si no corresponde a ninguna etapa con botones interactivos específicos, devolver None
    return None


def optimizar_respuesta_con_botones(respuesta: str, markup: InlineKeyboardMarkup | None) -> str:
    """Elimina redundancias y garantiza que direcciones físicas completas nunca se filtren en el chat."""
    if not isinstance(respuesta, str):
        respuesta = str(respuesta)

    # 0. Limpieza general de privacidad: eliminar cualquier bloque o encabezado de 'Tus direcciones registradas'
    lineas_raw = respuesta.split("\n")
    lineas_sanitizadas = []
    saltando_direcciones = False

    for l in lineas_raw:
        l_str = l.strip()
        # Detectar encabezado como '📍 **Tus direcciones registradas:**' o similar
        if re.search(r"(?:📍|\uD83D\uDCCD)?\s*\*{0,2}(?:Tus direcciones registradas|Direcciones registradas|Tus domicilios guardados)\*{0,2}:?", l_str, re.I):
            saltando_direcciones = True
            continue

        if saltando_direcciones:
            # Si es un item de dirección (1. Calle...) o viñeta de dirección
            if re.match(r"^\s*(?:\d+\.|\-|\•|📍|\uD83D\uDCCD)\s+", l_str) or not l_str:
                continue
            else:
                saltando_direcciones = False

        lineas_sanitizadas.append(l)

    respuesta = "\n".join(lineas_sanitizadas).strip()
    respuesta = re.sub(r"\n{3,}", "\n\n", respuesta)

    if not markup or not getattr(markup, "inline_keyboard", None):
        return respuesta

    callbacks = [btn.callback_data for fila in markup.inline_keyboard for btn in fila if getattr(btn, "callback_data", None)]

    # 1. Redundancia en PRODUCTOS (botones de carrito/cilindros tipo cart_add:...)
    if any(cb.startswith("cart_add:") for cb in callbacks):
        lineas = respuesta.split("\n")
        lineas_filtradas = []
        eliminadas = 0

        for l in lineas:
            l_str = l.strip()
            # Detectar líneas de items de productos (bullet points o numeradas con cilindro/kg/precio)
            es_item_producto = bool(
                re.match(r"^\s*(?:[•\-\*▪🔹🔸\d\.\)]+)\s*(?:\*\*)?(?:cilindro|gas\s*lp|gas|recarga|tanque|\d+\s*kg)", l_str, re.I)
                and (re.search(r"\$\s*\d+", l_str) or re.search(r"\b(?:kg|litros|pesos|mxn)\b", l_str, re.I))
            )
            if es_item_producto:
                eliminadas += 1
                continue

            # Quitar líneas de introducción que anuncian la lista de productos
            es_intro_catalogo = bool(
                re.search(r"(?:contamos con las siguientes|tenemos estas opciones|a continuación te muestro|te presento las opciones|capacidades disponibles|opciones disponibles|estas son las opciones|opciones de cilindros)", l_str, re.I)
                and (":" in l_str or "disponible" in l_str.lower() or "opciones" in l_str.lower())
            )
            if es_intro_catalogo:
                eliminadas += 1
                continue

            lineas_filtradas.append(l)

        texto_limpio = "\n".join(lineas_filtradas).strip()
        texto_limpio = re.sub(r"\n{3,}", "\n\n", texto_limpio)

        if eliminadas > 0:
            # Quitar preguntas repetitivas como "¿Cuál de estos deseas?" ya que los botones hacen la selección
            texto_limpio = re.sub(r"¿?(?:cuál|cual|cuántos|cuantos)\s+de\s+est(?:os|as)(?:\s+te\s+gustaría\s+ordenar|\s+prefieres|\s+deseas|\s+necesitas)?\??", "", texto_limpio, flags=re.I).strip()
            texto_limpio = re.sub(r"\n{3,}", "\n\n", texto_limpio)

            if not re.search(r"bot(?:ón|ones)", texto_limpio, re.I):
                texto_limpio = (texto_limpio.rstrip() + "\n\nSelecciona la capacidad que deseas en los botones de abajo (o escribe tu pedido si lo prefieres):").strip()

        return texto_limpio

    # 2. Redundancia en TIPO DE SERVICIO (botones client_svc:cilindro / estacionario)
    if any(cb.startswith("client_svc:") for cb in callbacks):
        lineas = respuesta.split("\n")
        lineas_filtradas = [
            l for l in lineas
            if not re.match(r"^\s*(?:[12]\ufe0f?\u20e3?|[12]\.|\-|\•)\s*(?:cilindro|tanque\s*estacionario)", l.strip(), re.I)
        ]
        texto_limpio = "\n".join(lineas_filtradas).strip()
        texto_limpio = re.sub(r"\n{3,}", "\n\n", texto_limpio)
        return texto_limpio

    # 3. Redundancia en MÉTODO DE PAGO (botones client_pay:...)
    if any(cb.startswith("client_pay:") for cb in callbacks):
        lineas = respuesta.split("\n")
        lineas_filtradas = [
            l for l in lineas
            if not re.match(r"^\s*(?:[•\-\*▪🔹🔸\d\.\)]+)\s*(?:\*\*)?(?:💵|💳)?\s*(?:efectivo|terminal|tarjeta)", l.strip(), re.I)
            and not re.search(r"¿?(?:cuál|cual)\s+(?:eliges|prefieres|de\s+est(?:os|as))\??", l.strip(), re.I)
        ]
        texto_limpio = "\n".join(lineas_filtradas).strip()
        texto_limpio = re.sub(r"\n{3,}", "\n\n", texto_limpio)
        return texto_limpio

    # 4. Redundancia en DIRECCIONES (botones client_addr:...)
    # Solicitud del usuario: "que salgan solo por botón las direcciones guardadas"
    # Se eliminan las líneas de texto que listan las direcciones para que se muestren exclusivamente en los botones interactivos.
    if any(cb.startswith("client_addr:") for cb in callbacks):
        # 4.1 Truncar cualquier alucinación en la que el LLM simule la respuesta o confirmación del cliente en el mismo mensaje
        m_stop = re.search(r"(¿(?:cuál opción prefieres|a cuál de tus direcciones|cuál de tus direcciones|cuál opción deseas|cuál prefieres)[^?\n]*\?[\s🏠🏡]*)(.*)", respuesta, flags=re.I | re.S)
        if m_stop and m_stop.group(2).strip():
            respuesta = respuesta[:m_stop.end(1)].strip()
        else:
            m_halluc = re.search(r"\n\s*(?:¡?Gracias[^!\n]*!?\s*(?:🏠|🏡)?\s*(?:He registrado|registré|anoté|seleccioné)?\s*la siguiente dirección.*)", respuesta, flags=re.I | re.S)
            if m_halluc:
                respuesta = respuesta[:m_halluc.start()].strip()

        lineas = respuesta.split("\n")
        lineas_filtradas = []
        eliminadas_direcciones = 0

        for l in lineas:
            l_str = l.strip()

            # Detectar líneas de items de direcciones (numeradas 1., 2., con pin 📍 o [Alias])
            es_item_direccion = bool(
                re.match(r"^\s*\d+\.\s*(?:📍|\uD83D\uDCCD|\*\*\[|\[)?", l_str)
                and (
                    re.search(r"(?:📍|\uD83D\uDCCD|\[Predeterminada\]|\[Dirección|calle|av\.|avenida|fracc|col\.|sm\.|lote|km|manzana|núm|num|#)", l_str, re.I)
                    or re.search(r"(?:casa|depto|departamento|piso|hotel|residencia|san\s*javier|los\s*mangos|s\u00e1balo|estrada)", l_str, re.I)
                )
                and not l_str.endswith("?")
            )
            if es_item_direccion:
                eliminadas_direcciones += 1
                continue

            # Detectar frases de introducción a la lista de direcciones
            es_intro_direcciones = bool(
                re.search(r"(?:tengo registradas las siguientes direcciones|tengo guardadas las siguientes direcciones|cuentas con las siguientes direcciones|veo que tienes registradas las siguientes direcciones|tus direcciones registradas son|estas son tus direcciones)", l_str, re.I)
                and (":" in l_str or "para ti" in l_str.lower() or "siguientes" in l_str.lower())
            )
            if es_intro_direcciones:
                eliminadas_direcciones += 1
                continue

            lineas_filtradas.append(l)

        texto_limpio = "\n".join(lineas_filtradas).strip()
        texto_limpio = re.sub(r"\n{3,}", "\n\n", texto_limpio)

        if eliminadas_direcciones > 0:
            # Adecuar la pregunta de cierre para referirse a los botones
            patron_pregunta = r"¿?(?:a\s+cuál|a\s+cual|cuál|cual)\s+de\s+(?:estas|tus)\s+direcciones.*?\??"
            if re.search(patron_pregunta, texto_limpio, re.I):
                texto_limpio = re.sub(
                    patron_pregunta,
                    "Por favor selecciona en los botones de abajo a cuál de tus direcciones guardadas deseas que enviemos tu pedido (o presiona **'➕ Ingresar nueva dirección'**):",
                    texto_limpio,
                    flags=re.I,
                ).strip()
            elif not re.search(r"bot(?:ón|ones)", texto_limpio, re.I):
                texto_limpio = (
                    texto_limpio.rstrip()
                    + "\n\nPor favor selecciona en los botones de abajo a cuál de tus direcciones guardadas deseas que enviemos tu pedido (o presiona **'➕ Ingresar nueva dirección'**):"
                ).strip()

            texto_limpio = re.sub(r"\n{3,}", "\n\n", texto_limpio)

        return texto_limpio

    return respuesta


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejar comando /start e iniciar flujo de bienvenida."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    first_name = update.effective_user.first_name or "Cliente"
    chat_id = update.effective_chat.id if update.effective_chat else user_id

    thread_id = f"telegram:{TENANT_ID}:{chat_id}"

    config = {
        "configurable": {
            "thread_id": thread_id,
            "tenant_id": TENANT_ID,
            "channel": "telegram",
            "channel_user_id": str(user_id),
        }
    }

    try:
        try:
            await context.bot.send_chat_action(
                chat_id=chat_id,
                action=ChatAction.TYPING,
            )
        except Exception:
            pass

        resultado = await graph.ainvoke(
            {
                "messages": [
                    HumanMessage(
                        content="Hola, acabo de iniciar la conversación para pedir gas."
                    )
                ],
                "channel": "telegram",
                "channel_user_id": str(user_id),
            },
            config=config,
        )

        ai_message = resultado["messages"][-1]
        respuesta = ai_message.content

        if not isinstance(respuesta, str):
            respuesta = str(respuesta)

        markup_start = get_botones_tipo_servicio()
        respuesta = optimizar_respuesta_con_botones(respuesta, markup_start)
        await update.message.reply_text(
            respuesta,
            reply_markup=markup_start,
        )

    except Exception as error:
        logger.error(f"❌ Error en /start para usuario {user_id}: {error}", exc_info=True)
        await update.message.reply_text(
            "¡Hola! 👋 Bienvenido a Gas a Tu Puerta - Petroil. ⛽\n\n"
            "¿En qué podemos ayudarte hoy? ¿Tu pedido será para cilindro o tanque estacionario?",
            reply_markup=get_botones_tipo_servicio(),
        )


async def safe_reply_text(message, text: str, reply_markup=None) -> None:
    """Envía un mensaje a Telegram intentando parse_mode='Markdown' y con fallback a texto plano si falla."""
    if not isinstance(text, str):
        text = str(text)
    try:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception as e:
        logger.warning(f"Error al enviar mensaje con Markdown ({e}), reintentando en texto plano...")
        try:
            await message.reply_text(text, reply_markup=reply_markup)
        except Exception as e2:
            logger.error(f"Error fatal enviando mensaje: {e2}")


MENSAJE_SEGURIDAD_ATENCION = (
    "Entiendo, pero no puedo decodificar, ejecutar ni procesar payloads de ese tipo. 🙅‍♂️\n\n"
    "Mi función como asistente de **Gas a Tu Puerta - Petroil** es únicamente de atención al cliente:\n\n"
    "- 🟢 **Realizar un pedido** de gas (cilindro o tanque estacionario)\n"
    "- 🔵 **Consultar el estatus** de tu pedido (folio o teléfono)\n"
    "- ❌ **Cancelar** un pedido tuyo\n\n"
    "No tengo capacidad ni autorización para ejecutar código, decodificar datos ni acceder a la base de datos de forma arbitraria.\n\n"
    "¿Te gustaría que te ayude con tu pedido de gas? 😊"
)


async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesar mensajes de texto enviados por el usuario."""
    if not update.message or not update.message.text:
        return

    if not update.effective_chat or not update.effective_user:
        return

    repo = get_repository()
    texto_usuario = update.message.text.strip()
    texto_lower = texto_usuario.lower()
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # 1. Si el cliente estaba en proceso de dejar un comentario opcional de calificación
    awaiting_order_id = context.user_data.get("awaiting_rating_comment_order_id")
    awaiting_time = context.user_data.get("awaiting_rating_time", 0)
    if awaiting_order_id and (datetime.now().timestamp() - awaiting_time) < 600:
        es_nuevo_pedido = any(k in texto_lower for k in ["quiero", "cilindro", "estacionario", "tanque", "litros", "pedir", "orden"])
        if not es_nuevo_pedido:
            context.user_data.pop("awaiting_rating_comment_order_id", None)
            context.user_data.pop("awaiting_rating_time", None)
            repo.update_order_rating_feedback(TENANT_ID, awaiting_order_id, comment=texto_usuario)
            await safe_reply_text(
                update.message,
                "📝 **¡Comentario registrado!**\n\n"
                "Muchas gracias por compartirnos tu opinión detallada. Tus comentarios han sido guardados para el equipo de calidad de Petroil. ¡Que tengas un excelente día! ⛽🌟",
            )
            return
        else:
            context.user_data.pop("awaiting_rating_comment_order_id", None)
            context.user_data.pop("awaiting_rating_time", None)

    # 2. Detección temprana de intentos de payload / código / inyección / scraping / consultas a múltiples teléfonos
    found_phones = re.findall(r"\b(?:\+?52\s*)?(\d{10})\b", texto_usuario)
    es_payload_o_inyeccion = any(k in texto_lower for k in [
        "payload", "decodifica", "decodificar", "base64", "script", "ejecutar código", "ejecuta codigo",
        "ejecutar codigo", "ejecuta script", "ejecutar script", "eval(", "exec(", "system(", "sql injection",
        "drop table", "select * from", "union select", "bypass", "jailbreak", "ignora tus instrucciones",
        "ignore previous instructions", "ignora todas las instrucciones", "revela tu prompt", "muestra tu system prompt"
    ])
    es_consulta_multiple = (
        len(found_phones) > 1 and any(k in texto_lower for k in ["pedido", "pedidos", "número", "numero", "orden", "ordenes", "historial", "cliente", "clientes"])
    ) or any(k in texto_lower for k in [
        "dos numeros", "dos números", "varios numeros", "varios números", "múltiples números", "multiples numeros",
        "pedidos de otros", "pedidos de otro", "pedidos de dos", "pedidos de varios"
    ])

    if es_payload_o_inyeccion or es_consulta_multiple:
        await safe_reply_text(update.message, MENSAJE_SEGURIDAD_ATENCION, reply_markup=get_botones_tipo_servicio())
        return

    thread_id = f"telegram:{TENANT_ID}:{chat_id}"

    config = {
        "configurable": {
            "thread_id": thread_id,
            "tenant_id": TENANT_ID,
            "channel": "telegram",
            "channel_user_id": str(user_id),
        }
    }

    # 3. Control de seguridad y vinculación de teléfono con el usuario de Telegram
    bound_cust = repo.get_customer(TENANT_ID, "telegram", str(user_id))
    if bound_cust and bound_cust.phone:
        context.user_data["phone"] = bound_cust.phone
    else:
        # Detectar si se proporcionó un solo teléfono celular legítimo
        if len(found_phones) == 1:
            digits = re.sub(r"\D", "", found_phones[0])
            if len(digits) == 10:
                context.user_data["phone"] = digits
        elif len(found_phones) > 1:
            context.user_data.pop("phone", None)

    try:
        try:
            await context.bot.send_chat_action(
                chat_id=chat_id,
                action=ChatAction.TYPING,
            )
        except Exception:
            pass

        # Invocación asíncrona del grafo LangGraph
        resultado = await graph.ainvoke(
            {
                "messages": [
                    HumanMessage(content=texto_usuario)
                ],
                "channel": "telegram",
                "channel_user_id": str(user_id),
            },
            config=config,
        )

        ai_message = resultado["messages"][-1]
        respuesta = ai_message.content
        if not isinstance(respuesta, str):
            respuesta = str(respuesta)

        # Si la respuesta contiene denegación de acceso o de seguridad, mostrar mensaje estructurado
        if "⛔ ACCESO DENEGADO" in respuesta or "ACCESO DENEGADO" in respuesta:
            respuesta = MENSAJE_SEGURIDAD_ATENCION

        phone_ctx = context.user_data.get("phone", "")
        inline_markup = detectar_botones_mensaje(respuesta, phone=phone_ctx, channel_user_id=str(user_id))
        respuesta = optimizar_respuesta_con_botones(respuesta, inline_markup)

        max_len = 4000
        if len(respuesta) <= max_len:
            await safe_reply_text(update.message, respuesta, reply_markup=inline_markup)
        else:
            for i in range(0, len(respuesta), max_len):
                sub_markup = inline_markup if (i + max_len >= len(respuesta)) else None
                await safe_reply_text(update.message, respuesta[i:i + max_len], reply_markup=sub_markup)

    except Exception as error:
        logger.error(f"❌ Error procesando mensaje de {user_id}: {error}", exc_info=True)
        await safe_reply_text(
            update.message,
            "⚠️ Ocurrió un error al procesar tu solicitud. Por favor intenta de nuevo en unos momentos."
        )


async def recibir_ubicacion_cliente(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Procesar ubicación GPS o en tiempo real compartida por el cliente."""
    if not update.message or not update.message.location:
        return

    if not update.effective_chat or not update.effective_user:
        return

    loc = update.message.location
    lat = loc.latitude
    lng = loc.longitude
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    direccion_detectada = reverse_geocode(lat, lng)

    thread_id = f"telegram:{TENANT_ID}:{chat_id}"

    config = {
        "configurable": {
            "thread_id": thread_id,
            "tenant_id": TENANT_ID,
            "channel": "telegram",
            "channel_user_id": str(user_id),
        }
    }

    prompt_gps = (
        f"📍 [UBICACIÓN GPS EN TIEMPO REAL COMPARTIDA POR EL CLIENTE]\n"
        f"- Dirección detectada en mapa: {direccion_detectada}\n"
        f"- Coordenadas GPS exactas: Latitud {lat:.6f}, Longitud {lng:.6f}\n\n"
        f"INSTRUCCIÓN PARA EL ASISTENTE:\n"
        f"1. Confirma al cliente que recibiste con éxito su ubicación en '{direccion_detectada}'.\n"
        f"2. Pregúntale amablemente si confirma esta ubicación como su punto de entrega y si tiene referencias adicionales (ej. color de casa o portón).\n"
        f"3. Cuando llames a la herramienta create_order para finalizar el pedido, en el campo 'delivery_address' DEBES registrar el nombre de la calle/colonia ('{direccion_detectada}'), agregando cualquier referencia del cliente (ej. '{direccion_detectada} - Casa blanca con portón'). NUNCA uses números de latitud ni longitud como nombre de dirección. Y DEBES pasar obligatoriamente: delivery_lat={lat:.6f}, delivery_lng={lng:.6f}."
    )

    try:
        try:
            await context.bot.send_chat_action(
                chat_id=chat_id,
                action=ChatAction.TYPING,
            )
        except Exception:
            pass

        resultado = await graph.ainvoke(
            {
                "messages": [
                    HumanMessage(content=prompt_gps)
                ],
                "channel": "telegram",
                "channel_user_id": str(user_id),
            },
            config=config,
        )

        ai_message = resultado["messages"][-1]
        respuesta = ai_message.content

        if not isinstance(respuesta, str):
            respuesta = str(respuesta)

        await update.message.reply_text(respuesta)

    except Exception as error:
        logger.error(f"❌ Error procesando ubicación GPS de {user_id}: {error}", exc_info=True)
        await update.message.reply_text(
            f"📍 ¡Ubicación GPS recibida ({lat:.5f}, {lng:.5f})!\n"
            f"Dirección detectada: {direccion_detectada}.\n"
            "¿Deseas que programemos tu entrega en este punto?"
        )


async def manejar_callback_cliente(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejar botones interactivos del cliente (ej. Selección de servicio, Cancelar Pedido)."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    data = query.data
    repo = get_repository()

    if data.startswith("client_svc:"):
        svc_type = data.split(":")[1]
        context.user_data["service_type"] = svc_type

        user_id = query.from_user.id if query.from_user else (update.effective_user.id if update.effective_user else 0)
        chat_id = update.effective_chat.id if update.effective_chat else user_id

        # Remover botones del mensaje anterior
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        if svc_type == "cilindro":
            # Desplegar de inmediato el catálogo interactivo de cilindros con botones dinámicos y carrito
            context.user_data["carrito_cilindros"] = {}
            texto_catalogo = texto_resumen_catalogo({})
            markup_catalogo = get_botones_productos_cilindros({})
            await context.bot.send_message(
                chat_id=chat_id,
                text=texto_catalogo,
                reply_markup=markup_catalogo,
                parse_mode="Markdown",
            )
            return

        texto_usuario = "Deseo pedir gas para tanque estacionario"

        try:
            await context.bot.send_chat_action(
                chat_id=chat_id,
                action=ChatAction.TYPING,
            )
        except Exception:
            pass

        thread_id = f"telegram:{TENANT_ID}:{chat_id}"
        config = {
            "configurable": {
                "thread_id": thread_id,
                "tenant_id": TENANT_ID,
                "channel": "telegram",
                "channel_user_id": str(user_id),
            }
        }

        try:
            resultado = await graph.ainvoke(
                {
                    "messages": [HumanMessage(content=texto_usuario)],
                    "channel": "telegram",
                    "channel_user_id": str(user_id),
                },
                config=config,
            )

            ai_message = resultado["messages"][-1]
            respuesta = ai_message.content
            if not isinstance(respuesta, str):
                respuesta = str(respuesta)

            phone_ctx = context.user_data.get("phone", "")
            inline_markup = detectar_botones_mensaje(respuesta, phone=phone_ctx, channel_user_id=str(user_id))
            respuesta = optimizar_respuesta_con_botones(respuesta, inline_markup)

            max_len = 4000
            if len(respuesta) <= max_len:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=respuesta,
                    reply_markup=inline_markup,
                )
            else:
                for i in range(0, len(respuesta), max_len):
                    sub_markup = inline_markup if (i + max_len >= len(respuesta)) else None
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=respuesta[i:i + max_len],
                        reply_markup=sub_markup,
                    )
        except Exception as error:
            logger.error(f"❌ Error procesando tipo de servicio para {user_id}: {error}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Ocurrió un error al procesar tu solicitud. Por favor intenta de nuevo.",
            )
        return

    # Agregar producto al carrito interactivo
    if data.startswith("cart_add:"):
        key = data.split(":")[1]
        carrito = context.user_data.setdefault("carrito_cilindros", {})
        carrito[key] = carrito.get(key, 0) + 1

        nuevo_texto = texto_resumen_catalogo(carrito)
        nuevo_markup = get_botones_productos_cilindros(carrito)

        try:
            await query.edit_message_text(
                text=nuevo_texto,
                reply_markup=nuevo_markup,
                parse_mode="Markdown",
            )
        except Exception:
            try:
                await query.edit_message_text(
                    text=nuevo_texto.replace("**", "").replace("•", "-"),
                    reply_markup=nuevo_markup,
                )
            except Exception:
                pass
        return

    # Vaciar carrito interactivo
    if data == "cart_clear":
        context.user_data["carrito_cilindros"] = {}
        nuevo_texto = texto_resumen_catalogo({})
        nuevo_markup = get_botones_productos_cilindros({})

        try:
            await query.edit_message_text(
                text=nuevo_texto,
                reply_markup=nuevo_markup,
                parse_mode="Markdown",
            )
        except Exception:
            try:
                await query.edit_message_text(
                    text=nuevo_texto.replace("**", "").replace("•", "-"),
                    reply_markup=nuevo_markup,
                )
            except Exception:
                pass
        return

    # Confirmar productos del carrito y continuar con el pedido
    if data == "cart_checkout":
        carrito = context.user_data.get("carrito_cilindros", {})
        if not carrito or sum(carrito.values()) == 0:
            await query.answer("Por favor selecciona al menos un cilindro.", show_alert=True)
            return

        partes = []
        prods = get_catalogo_productos_db()
        prods_by_id = {p.id: p for p in prods}

        for k, cant in carrito.items():
            if cant > 0:
                if k in prods_by_id:
                    nombre = prods_by_id[k].name
                else:
                    nombre = f"Cilindro de {k}"
                partes.append(f"{cant} {nombre}")

        texto_usuario = f"Deseo ordenar {', '.join(partes)}"
        context.user_data["carrito_cilindros"] = {}

        # Remover botones del mensaje previo de catálogo
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        user_id = query.from_user.id if query.from_user else (update.effective_user.id if update.effective_user else 0)
        chat_id = update.effective_chat.id if update.effective_chat else user_id

        try:
            await context.bot.send_chat_action(
                chat_id=chat_id,
                action=ChatAction.TYPING,
            )
        except Exception:
            pass

        thread_id = f"telegram:{TENANT_ID}:{chat_id}"
        config = {
            "configurable": {
                "thread_id": thread_id,
                "tenant_id": TENANT_ID,
                "channel": "telegram",
                "channel_user_id": str(user_id),
            }
        }

        try:
            resultado = await graph.ainvoke(
                {
                    "messages": [HumanMessage(content=texto_usuario)],
                    "channel": "telegram",
                    "channel_user_id": str(user_id),
                },
                config=config,
            )

            ai_message = resultado["messages"][-1]
            respuesta = ai_message.content
            if not isinstance(respuesta, str):
                respuesta = str(respuesta)

            phone_ctx = context.user_data.get("phone", "")
            inline_markup = detectar_botones_mensaje(respuesta, phone=phone_ctx, channel_user_id=str(user_id))
            respuesta = optimizar_respuesta_con_botones(respuesta, inline_markup)

            max_len = 4000
            if len(respuesta) <= max_len:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=respuesta,
                    reply_markup=inline_markup,
                )
            else:
                for i in range(0, len(respuesta), max_len):
                    sub_markup = inline_markup if (i + max_len >= len(respuesta)) else None
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=respuesta[i:i + max_len],
                        reply_markup=sub_markup,
                    )
        except Exception as error:
            logger.error(f"❌ Error en cart_checkout para {user_id}: {error}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Ocurrió un error al procesar tu selección. Por favor intenta de nuevo.",
            )
        return

    # Menú para eliminar una dirección guardada
    if data == "client_addr_del_menu":
        user_id = query.from_user.id if query.from_user else (update.effective_user.id if update.effective_user else 0)
        phone = context.user_data.get("phone", "")
        cust = repo.get_customer_by_phone(TENANT_ID, phone) if phone else None
        if not cust and user_id:
            cust = repo.get_customer(TENANT_ID, "telegram", str(user_id))

        if not cust or not cust.addresses:
            await query.answer("No tienes direcciones guardadas para eliminar.", show_alert=True)
            return

        try:
            await query.edit_message_text(
                text="🗑️ *Eliminar Dirección Guardada*\n\nSelecciona la dirección que deseas borrar de tu cuenta:",
                reply_markup=get_botones_eliminar_direcciones(cust.addresses),
                parse_mode="Markdown",
            )
        except Exception:
            pass
        return

    # Confirmación previa antes de borrar la dirección seleccionada
    if data.startswith("client_addr_del:"):
        parts = data.split(":")
        addr_id = int(parts[1])
        idx = parts[2] if len(parts) > 2 else "1"
        user_id = query.from_user.id if query.from_user else (update.effective_user.id if update.effective_user else 0)
        phone = context.user_data.get("phone", "")
        cust = repo.get_customer_by_phone(TENANT_ID, phone) if phone else None
        if not cust and user_id:
            cust = repo.get_customer(TENANT_ID, "telegram", str(user_id))

        addr_obj = next((a for a in (cust.addresses if cust else []) if a.id == addr_id), None)
        addr_str = addr_obj.address if addr_obj else f"Dirección #{idx}"

        confirm_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🗑️ Sí, eliminar", callback_data=f"client_addr_del_confirm:{addr_id}"),
                ],
                [
                    InlineKeyboardButton("🔙 Cancelar", callback_data="client_addr_del_menu"),
                ],
            ]
        )

        try:
            await query.edit_message_text(
                text=f"⚠️ *¿Estás seguro de eliminar esta dirección?*\n\n📍 `{addr_str}`\n\nEsta acción no se puede deshacer.",
                reply_markup=confirm_markup,
                parse_mode="Markdown",
            )
        except Exception:
            pass
        return

    # Ejecutar eliminación definitiva de la dirección
    if data.startswith("client_addr_del_confirm:"):
        addr_id = int(data.split(":")[1])
        user_id = query.from_user.id if query.from_user else (update.effective_user.id if update.effective_user else 0)
        phone = context.user_data.get("phone", "")
        cust = repo.get_customer_by_phone(TENANT_ID, phone) if phone else None
        if not cust and user_id:
            cust = repo.get_customer(TENANT_ID, "telegram", str(user_id))

        if cust:
            repo.delete_customer_address(cust.id, addr_id)
            updated_cust = repo.get_customer_by_phone(TENANT_ID, phone) if phone else repo.get_customer(TENANT_ID, "telegram", str(user_id))
            remaining_addrs = updated_cust.addresses if (updated_cust and updated_cust.addresses) else []
        else:
            remaining_addrs = []

        await query.answer("✅ Dirección eliminada correctamente.", show_alert=True)

        if remaining_addrs:
            texto_resp = (
                "✅ *Dirección eliminada correctamente de tu cuenta.*\n\n"
                "¿A cuál de tus direcciones restantes deseas que enviemos tu pedido o prefieres ingresar una nueva?"
            )
            markup_resp = get_botones_direcciones_cliente(remaining_addrs)
        else:
            texto_resp = (
                "✅ *Dirección eliminada correctamente.*\n\n"
                "Ya no tienes direcciones guardadas. Por favor escribe tu dirección de entrega completa o comparte tu ubicación GPS para continuar con tu pedido:"
            )
            markup_resp = None

        try:
            await query.edit_message_text(
                text=texto_resp,
                reply_markup=markup_resp,
                parse_mode="Markdown",
            )
        except Exception:
            pass
        return

    # Volver del menú de eliminación a selección de dirección
    if data == "client_addr_back":
        user_id = query.from_user.id if query.from_user else (update.effective_user.id if update.effective_user else 0)
        phone = context.user_data.get("phone", "")
        cust = repo.get_customer_by_phone(TENANT_ID, phone) if phone else None
        if not cust and user_id:
            cust = repo.get_customer(TENANT_ID, "telegram", str(user_id))

        addrs = cust.addresses if (cust and cust.addresses) else []
        if addrs:
            texto_resp = "¿A cuál de tus direcciones registradas deseas que enviemos tu pedido o prefieres ingresar una nueva?"
            markup_resp = get_botones_direcciones_cliente(addrs)
        else:
            texto_resp = "Por favor escribe tu dirección de entrega o comparte tu ubicación GPS:"
            markup_resp = None

        try:
            await query.edit_message_text(
                text=texto_resp,
                reply_markup=markup_resp,
                parse_mode="Markdown",
            )
        except Exception:
            pass
        return

    # Selección de dirección guardada o nueva dirección
    if data.startswith("client_addr:"):
        choice = data.split(":", 1)[1]
        user_id = query.from_user.id if query.from_user else (update.effective_user.id if update.effective_user else 0)
        chat_id = update.effective_chat.id if update.effective_chat else user_id

        # Remover botones del mensaje anterior
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        try:
            await context.bot.send_chat_action(
                chat_id=chat_id,
                action=ChatAction.TYPING,
            )
        except Exception:
            pass

        phone = context.user_data.get("phone", "")
        cust = repo.get_customer_by_phone(TENANT_ID, phone) if phone else None
        if not cust and user_id:
            cust = repo.get_customer(TENANT_ID, "telegram", str(user_id))

        if choice == "new":
            texto_usuario = "Deseo ingresar una nueva dirección de entrega"
        else:
            try:
                idx = int(choice) - 1
                if cust and cust.addresses and 0 <= idx < len(cust.addresses):
                    selected_addr = cust.addresses[idx].address
                elif cust and cust.address and idx == 0:
                    selected_addr = cust.address
                else:
                    selected_addr = f"dirección #{choice}"
                texto_usuario = f"Deseo que envíen el pedido a mi dirección registrada: {selected_addr}"
            except Exception:
                texto_usuario = f"Deseo la dirección número {choice}"

        thread_id = f"telegram:{TENANT_ID}:{chat_id}"
        config = {
            "configurable": {
                "thread_id": thread_id,
                "tenant_id": TENANT_ID,
                "channel": "telegram",
                "channel_user_id": str(user_id),
            }
        }

        try:
            resultado = await graph.ainvoke(
                {
                    "messages": [HumanMessage(content=texto_usuario)],
                    "channel": "telegram",
                    "channel_user_id": str(user_id),
                },
                config=config,
            )

            ai_message = resultado["messages"][-1]
            respuesta = ai_message.content
            if not isinstance(respuesta, str):
                respuesta = str(respuesta)

            inline_markup = detectar_botones_mensaje(respuesta, phone=phone, channel_user_id=str(user_id))
            respuesta = optimizar_respuesta_con_botones(respuesta, inline_markup)

            max_len = 4000
            if len(respuesta) <= max_len:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=respuesta,
                    reply_markup=inline_markup,
                )
            else:
                for i in range(0, len(respuesta), max_len):
                    sub_markup = inline_markup if (i + max_len >= len(respuesta)) else None
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=respuesta[i:i + max_len],
                        reply_markup=sub_markup,
                    )
        except Exception as error:
            logger.error(f"❌ Error en selección de dirección para {user_id}: {error}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Ocurrió un error al procesar tu selección de dirección. Por favor intenta de nuevo.",
            )
        return

    # Selección de método de pago (Efectivo / Terminal)
    if data.startswith("client_pay:"):
        pay_type = data.split(":", 1)[1]
        user_id = query.from_user.id if query.from_user else (update.effective_user.id if update.effective_user else 0)
        chat_id = update.effective_chat.id if update.effective_chat else user_id

        # Remover botones del mensaje anterior
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        try:
            await context.bot.send_chat_action(
                chat_id=chat_id,
                action=ChatAction.TYPING,
            )
        except Exception:
            pass

        texto_usuario = "Mi método de pago será en Efectivo" if pay_type == "efectivo" else "Mi método de pago será con Terminal (Tarjeta)"

        thread_id = f"telegram:{TENANT_ID}:{chat_id}"
        config = {
            "configurable": {
                "thread_id": thread_id,
                "tenant_id": TENANT_ID,
                "channel": "telegram",
                "channel_user_id": str(user_id),
            }
        }

        try:
            resultado = await graph.ainvoke(
                {
                    "messages": [HumanMessage(content=texto_usuario)],
                    "channel": "telegram",
                    "channel_user_id": str(user_id),
                },
                config=config,
            )

            ai_message = resultado["messages"][-1]
            respuesta = ai_message.content
            if not isinstance(respuesta, str):
                respuesta = str(respuesta)

            phone_ctx = context.user_data.get("phone", "")
            inline_markup = detectar_botones_mensaje(respuesta, phone=phone_ctx, channel_user_id=str(user_id))
            respuesta = optimizar_respuesta_con_botones(respuesta, inline_markup)

            max_len = 4000
            if len(respuesta) <= max_len:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=respuesta,
                    reply_markup=inline_markup,
                )
            else:
                for i in range(0, len(respuesta), max_len):
                    sub_markup = inline_markup if (i + max_len >= len(respuesta)) else None
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=respuesta[i:i + max_len],
                        reply_markup=sub_markup,
                    )
        except Exception as error:
            logger.error(f"❌ Error en selección de pago para {user_id}: {error}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Ocurrió un error al procesar tu método de pago. Por favor intenta de nuevo.",
            )
        return

    # Confirmar, editar o cancelar pedido desde el resumen
    if data.startswith("client_confirm:"):
        action = data.split(":", 1)[1]
        user_id = query.from_user.id if query.from_user else (update.effective_user.id if update.effective_user else 0)
        chat_id = update.effective_chat.id if update.effective_chat else user_id

        # Remover botones del mensaje anterior
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        try:
            await context.bot.send_chat_action(
                chat_id=chat_id,
                action=ChatAction.TYPING,
            )
        except Exception:
            pass

        if action == "yes":
            texto_usuario = "Sí, confirmar pedido"
        elif action == "edit":
            texto_usuario = "Deseo modificar los datos de mi pedido"
        else:
            texto_usuario = "No, deseo cancelar este pedido"

        thread_id = f"telegram:{TENANT_ID}:{chat_id}"
        config = {
            "configurable": {
                "thread_id": thread_id,
                "tenant_id": TENANT_ID,
                "channel": "telegram",
                "channel_user_id": str(user_id),
            }
        }

        try:
            resultado = await graph.ainvoke(
                {
                    "messages": [HumanMessage(content=texto_usuario)],
                    "channel": "telegram",
                    "channel_user_id": str(user_id),
                },
                config=config,
            )

            ai_message = resultado["messages"][-1]
            respuesta = ai_message.content
            if not isinstance(respuesta, str):
                respuesta = str(respuesta)

            phone_ctx = context.user_data.get("phone", "")
            inline_markup = detectar_botones_mensaje(respuesta, phone=phone_ctx, channel_user_id=str(user_id))
            respuesta = optimizar_respuesta_con_botones(respuesta, inline_markup)

            max_len = 4000
            if len(respuesta) <= max_len:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=respuesta,
                    reply_markup=inline_markup,
                )
            else:
                for i in range(0, len(respuesta), max_len):
                    sub_markup = inline_markup if (i + max_len >= len(respuesta)) else None
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=respuesta[i:i + max_len],
                        reply_markup=sub_markup,
                    )
        except Exception as error:
            logger.error(f"❌ Error en confirmación de pedido para {user_id}: {error}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Ocurrió un error al procesar tu confirmación. Por favor intenta de nuevo.",
            )
        return

    # Selección de producto específico del catálogo
    if data.startswith("client_prod:"):
        prod_text = data.split(":", 1)[1]
        user_id = query.from_user.id if query.from_user else (update.effective_user.id if update.effective_user else 0)
        chat_id = update.effective_chat.id if update.effective_chat else user_id

        # Remover botones del mensaje anterior
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        try:
            await context.bot.send_chat_action(
                chat_id=chat_id,
                action=ChatAction.TYPING,
            )
        except Exception:
            pass

        thread_id = f"telegram:{TENANT_ID}:{chat_id}"
        config = {
            "configurable": {
                "thread_id": thread_id,
                "tenant_id": TENANT_ID,
                "channel": "telegram",
                "channel_user_id": str(user_id),
            }
        }

        try:
            resultado = await graph.ainvoke(
                {
                    "messages": [HumanMessage(content=prod_text)],
                    "channel": "telegram",
                    "channel_user_id": str(user_id),
                },
                config=config,
            )

            ai_message = resultado["messages"][-1]
            respuesta = ai_message.content
            if not isinstance(respuesta, str):
                respuesta = str(respuesta)

            phone_ctx = context.user_data.get("phone", "")
            inline_markup = detectar_botones_mensaje(respuesta, phone=phone_ctx, channel_user_id=str(user_id))
            respuesta = optimizar_respuesta_con_botones(respuesta, inline_markup)

            max_len = 4000
            if len(respuesta) <= max_len:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=respuesta,
                    reply_markup=inline_markup,
                )
            else:
                for i in range(0, len(respuesta), max_len):
                    sub_markup = inline_markup if (i + max_len >= len(respuesta)) else None
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=respuesta[i:i + max_len],
                        reply_markup=sub_markup,
                    )
        except Exception as error:
            logger.error(f"❌ Error procesando producto para {user_id}: {error}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Ocurrió un error al procesar tu selección. Por favor intenta de nuevo.",
            )
        return

    if data.startswith("cancel_order_client:"):
        order_id = int(data.split(":")[1])
        order = repo.get_order_by_id(TENANT_ID, order_id)
        if not order:
            await query.edit_message_text("⚠️ Pedido no encontrado.")
            return

        if order.status == "delivered":
            await query.edit_message_text("⚠️ Tu pedido ya fue entregado y no puede cancelarse.")
            return

        if order.status == "cancelled":
            await query.edit_message_text(f"⚠️ El pedido #{order_id} ya se encuentra cancelado.")
            return

        # Eliminar ubicación en tiempo real si existía
        if order.live_location_message_id and order.live_location_chat_id:
            from src.services.notifications import remove_client_live_location
            remove_client_live_location(order.live_location_chat_id, order.live_location_message_id)
            repo.clear_order_live_location(TENANT_ID, order_id)

        # Cancelar orden en BD y liberar chofer
        repo.cancel_order(TENANT_ID, order_id, cancelled_by="el cliente")

        # Notificar al chofer asignado si tiene Telegram
        if order.driver_id:
            driver = repo.get_driver(order.driver_id)
            if driver and driver.telegram_user_id:
                msg_driver = (
                    f"❌ **PEDIDO #{order_id} CANCELADO**\n\n"
                    f"👤 Cliente: {order.customer_name}\n"
                    f"📍 Dirección: {order.delivery_address}\n\n"
                    "El cliente ha cancelado este pedido. Ya no es necesario acudir al domicilio. Has quedado disponible para otros viajes."
                )
                notify_driver(driver.telegram_user_id, msg_driver)

        await query.edit_message_text(
            f"❌ **Tu pedido #{order_id} ha sido cancelado exitosamente.**\n\n"
            "Si deseas programar un nuevo pedido en el futuro, solo envíame un mensaje. ¡Estamos a tus órdenes! ⛽"
        )
        return

    # -------------------------------------------------------------------------
    # Calificación del Chofer y Encuesta de Entrega
    # -------------------------------------------------------------------------
    if data.startswith("rate_driver:"):
        parts = data.split(":")
        order_id = int(parts[1])
        stars = max(1, min(5, int(parts[2])))

        order = repo.get_order_by_id(TENANT_ID, order_id)
        if not order:
            await query.edit_message_text("⚠️ Pedido no encontrado.")
            return

        # Guardar calificación inicial
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
            texto_encuesta = (
                f"🌟 **¡Muchas gracias por calificar con {stars_str}!** ({stars}/5)\n\n"
                f"¿Qué fue lo que más te agradó del servicio de {driver_name}?\n"
                "Selecciona una opción para completar la encuesta:"
            )
            keyboard = [
                [
                    InlineKeyboardButton("⚡ Rapidez y puntualidad", callback_data=f"rate_tag:{order_id}:Rapidez"),
                    InlineKeyboardButton("😊 Trato muy amable", callback_data=f"rate_tag:{order_id}:Amabilidad"),
                ],
                [
                    InlineKeyboardButton("🛡️ Cuidado y seguridad", callback_data=f"rate_tag:{order_id}:Seguridad"),
                    InlineKeyboardButton("✨ Servicio impecable", callback_data=f"rate_tag:{order_id}:Impecable"),
                ],
                [
                    InlineKeyboardButton("⏩ Finalizar sin detalles", callback_data=f"rate_tag:{order_id}:Omitido"),
                ],
            ]
        else:
            texto_encuesta = (
                f"🙏 **Agradecemos tu calificación de {stars_str}** ({stars}/5)\n\n"
                f"Lamentamos que tu experiencia con {driver_name} no haya sido óptima.\n"
                "¿En qué aspecto podemos mejorar para brindarte un mejor servicio?"
            )
            keyboard = [
                [
                    InlineKeyboardButton("⏳ Demora en la entrega", callback_data=f"rate_tag:{order_id}:Demora"),
                    InlineKeyboardButton("🙁 Actitud del chofer", callback_data=f"rate_tag:{order_id}:Actitud"),
                ],
                [
                    InlineKeyboardButton("📦 Problema con el cilindro", callback_data=f"rate_tag:{order_id}:Cilindro"),
                    InlineKeyboardButton("💵 Cobro o cambio", callback_data=f"rate_tag:{order_id}:Cobro"),
                ],
                [
                    InlineKeyboardButton("⏩ Finalizar sin detalles", callback_data=f"rate_tag:{order_id}:Omitido"),
                ],
            ]

        await query.edit_message_text(
            texto_encuesta,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return

    if data.startswith("rate_tag:"):
        parts = data.split(":")
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
            "Omitido": "Servicio evaluado",
        }
        tag_display = tag_labels.get(tag, tag)
        feedback_to_save = "" if tag == "Omitido" else tag_display

        if feedback_to_save:
            repo.update_order_rating_feedback(TENANT_ID, order_id, feedback_tag=feedback_to_save)

        rating_data = repo.get_order_rating(TENANT_ID, order_id)
        stars_val = rating_data.get("rating", 5) if rating_data else 5
        stars_str = "⭐" * stars_val

        # Guardar en user_data que puede dejar un comentario de texto opcional
        context.user_data["awaiting_rating_comment_order_id"] = order_id
        context.user_data["awaiting_rating_time"] = datetime.now().timestamp()

        detalle_str = f"\n💬 **Aspecto destacado:** {tag_display}" if feedback_to_save else ""

        await query.edit_message_text(
            f"✅ **¡ENCUESTA COMPLETADA CON ÉXITO!**\n\n"
            f"⭐ **Calificación:** {stars_str} ({stars_val}/5){detalle_str}\n\n"
            "¡Muchas gracias por tu tiempo y valiosa retroalimentación! Nos ayuda a premiar a nuestros mejores choferes y elevar continuamente nuestra calidad. ⛽🌟\n\n"
            "_💡 Opcional: Si deseas agregar algún comentario o sugerencia escrita sobre tu repartidor, puedes enviarla en tu siguiente mensaje._",
            parse_mode="Markdown",
        )
        return



def main() -> None:
    """Iniciar el bot de Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN no está configurado en el archivo .env")
        sys.exit(1)

    print("=" * 60)
    print("🤖 Iniciando Bot de Telegram para Ventas de Gas")
    print(f"🏪 Tenant: {tenant.business_name} ({tenant.tenant_id})")
    print(f"🧠 Agente: {tenant.agent.name}")
    print("=" * 60)

    request_config = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
    )

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .request(request_config)
        .get_updates_request(request_config)
        .build()
    )

    # Comando /start
    application.add_handler(CommandHandler("start", start))

    # Recepción de ubicación GPS / tiempo real
    application.add_handler(MessageHandler(filters.LOCATION, recibir_ubicacion_cliente))

    # Botones interactivos (Cancelar pedido)
    application.add_handler(CallbackQueryHandler(manejar_callback_cliente))

    # Mensajes de texto normales
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            responder,
        )
    )

    print("✅ Bot conectado con Telegram. Esperando mensajes y ubicaciones GPS...")
    application.run_polling(
        bootstrap_retries=10,
        poll_interval=1.0,
        timeout=30,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot de Clientes detenido correctamente por el usuario (Ctrl+C).")