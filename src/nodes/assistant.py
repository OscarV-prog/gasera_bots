"""Node: LLM assistant — the core chat node.

Loads tenant config, builds the system prompt, binds tools,
and invokes the model. Uses Command for routing: if the LLM
makes tool calls → go to "tools", otherwise → END.
"""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import SystemMessage, trim_messages
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.config.llm_provider import create_llm
from src.config.tenant_config import TenantConfig, get_tenant
from src.state.agent_state import SalesAgentState
from src.tools import (
    ALL_TOOLS,
    cancel_order,
    create_order,
    delete_customer_address,
    get_customer_info,
    get_order_status,
    get_promotions,
    search_by_image,
    search_products,
    send_product_image,
)


def get_tenant_tools(tc: TenantConfig) -> list:
    """Select only the tools enabled for the given tenant."""
    tools = [
        search_products,
        create_order,
        get_order_status,
        get_customer_info,
        cancel_order,
        delete_customer_address,
    ]
    if getattr(tc.features, "image_search", False):
        tools.append(search_by_image)
        tools.append(send_product_image)
    if getattr(tc.features, "promotions", False):
        tools.append(get_promotions)
    return tools


def _build_system_prompt(tenant_id: str, channel: str | None = None) -> str:
    """Build a concise, efficient system prompt from the tenant's config."""
    tc = get_tenant(tenant_id)
    agent = tc.agent

    channel_hint = f"Canal de atención: {channel}.\n\n" if channel else ""
    rules_text = "\n".join(f"- {r}" for r in agent.rules) if agent.rules else ""
    rules_section = f"\n\n## Reglas Clave\n{rules_text}" if rules_text else ""

    # Inyectar catálogo oficial de productos del repositorio en el prompt del sistema
    catalog_section = ""
    try:
        from src.repositories import get_repository
        repo = get_repository()
        prods = repo.get_all_products(tenant_id)
        if prods:
            lines = [f"• {p.name} ({p.category}): ${p.price:,.2f} {p.currency}" for p in prods if p.in_stock]
            catalog_section = (
                f"\n\n## Catálogo Oficial de Productos Disponibles en el Sistema:\n"
                + "\n".join(lines)
                + "\n\nIMPORTANTE: Todos los productos y capacidades listados arriba están 100% DISPONIBLES y autorizados para venta. "
                + "Si el cliente solicita o selecciona cualquiera de ellos (incluyendo cilindros de 5 kg, 10 kg, 20 kg, 30 kg o 45 kg, o recarga de tanque estacionario), "
                + "NUNCA digas que no cuentas con él; acéptalo de inmediato y continúa con el siguiente paso del pedido (pedir teléfono o dirección de entrega)."
            )
    except Exception:
        pass

    lang_hint = ""
    if tc.language and tc.language != "es":
        lang_hint = f"\n\n## Idioma\nResponde en idioma: {tc.language}."

    return (
        f"Eres {agent.name}, {agent.role} de {tc.business_name}.\n\n"
        f"{channel_hint}"
        f"{agent.personality.strip()}"
        f"{catalog_section}"
        f"{rules_section}"
        f"{lang_hint}"
    )


async def assistant_node(
    state: SalesAgentState,
    config: RunnableConfig,
) -> Command[Literal["tools", "__end__"]]:
    """Invoke the LLM and route based on whether it made tool calls."""
    tenant_id = config["configurable"]["tenant_id"]
    tc = get_tenant(tenant_id)

    # Bind only the active tools configured for this tenant
    active_tools = get_tenant_tools(tc)
    model = create_llm(tc).bind_tools(active_tools)

    # Prepare messages: system prompt + trimmed conversation history
    channel = state.get("channel")
    system = SystemMessage(content=_build_system_prompt(tenant_id, channel))

    raw_history = state.get("messages", [])
    if raw_history:
        # Keep full order flow with generous sliding window (up to 25 messages),
        # ensuring it starts on a human message and preserves tool call pairs.
        trimmed_history = trim_messages(
            raw_history,
            max_tokens=25,
            strategy="last",
            token_counter=len,
            start_on="human",
            include_system=False,
            allow_partial=False,
        )
        if not trimmed_history:
            trimmed_history = raw_history[-2:]
    else:
        trimmed_history = []

    messages = [system] + list(trimmed_history)

    # Invoke
    response = await model.ainvoke(messages, config=config)

    # Route: tool calls → tools node, otherwise → end
    if response.tool_calls:
        return Command(
            update={"messages": [response]},
            goto="tools",
        )

    return Command(
        update={"messages": [response]},
        goto="__end__",
    )
