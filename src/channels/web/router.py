"""Web channel adapter.

Uses SSE streaming, keeping the existing Sales Studio API intact.
"""

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from langchain_core.messages import HumanMessage

from src.config.tenant_config import get_tenant, list_tenants
from src.graphs.sales_graph import build_sales_graph
from langgraph.checkpoint.memory import InMemorySaver

router = APIRouter()

# Keep graph checkpointing in memory for Web UI
_checkpointer = InMemorySaver()
_graph = build_sales_graph().compile(checkpointer=_checkpointer)

# Serve the index.html from where we moved it
# We'll put index.html inside src/channels/web/index.html
WEB_DIR = Path(__file__).parent


@router.get("/", response_class=HTMLResponse)
async def index():
    return (WEB_DIR / "index.html").read_text(encoding="utf-8")


@router.get("/api/tenants")
async def tenants_list():
    result = []
    for tid in list_tenants():
        tc = get_tenant(tid)
        result.append({
            "id": tid,
            "business_name": tc.business_name,
            "agent_name": tc.agent.name,
            "agent_role": tc.agent.role,
            "language": tc.language,
            "provider": f"{tc.llm.provider}/{tc.llm.model}",
        })
    return result


@router.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    tenant_id = body["tenant_id"]
    thread_id = body.get("thread_id") or f"{tenant_id}:{uuid.uuid4().hex[:8]}"
    message = body["message"]
    image_url = body.get("image_url")
    
    # Map to state input
    if image_url:
        content = [
            {"type": "text", "text": message or "What similar products do you have?"},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]
    else:
        content = message

    config = {
        "configurable": {
            "thread_id": thread_id, 
            "tenant_id": tenant_id
        }
    }
    
    # Let graph know about channel context
    state_updates = {"channel": "web", "channel_user_id": thread_id}
    # Currently astream_events doesn't let us pass initial keys easily except via messages, 
    # but langgraph allows updating state if we do graph.update_state()
    # Alternatively, just inject a HumanMessage.
    
    # We should add the state_updates inside the input dictionary:
    input_data = {
        "messages": [HumanMessage(content=content)],
        "channel": "web",
        "channel_user_id": thread_id
    }

    def _evt(data: dict) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def stream():
        yield _evt({"type": "meta", "thread_id": thread_id})

        try:
            async for event in _graph.astream_events(
                input_data,
                config=config,
                version="v2",
            ):
                kind = event["event"]
                name = event.get("name", "")

                if kind == "on_chain_start" and name in ("assistant", "tools"):
                    yield _evt({"type": "node_start", "node": name})

                elif kind == "on_chain_end" and name in ("assistant", "tools"):
                    yield _evt({"type": "node_end", "node": name})

                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and isinstance(chunk.content, str) and chunk.content:
                        yield _evt({"type": "token", "content": chunk.content})

                elif kind == "on_chat_model_end":
                    out = event["data"]["output"]
                    usage = {}
                    if hasattr(out, "usage_metadata") and out.usage_metadata:
                        um = out.usage_metadata
                        usage = {
                            "input": um.get("input_tokens", 0),
                            "output": um.get("output_tokens", 0),
                        }
                    tool_calls = []
                    if hasattr(out, "tool_calls") and out.tool_calls:
                        tool_calls = [{"name": tc["name"], "args": tc["args"]} for tc in out.tool_calls]
                    yield _evt({"type": "llm_end", "usage": usage, "tool_calls": tool_calls})

                elif kind == "on_tool_start":
                    inp = event["data"].get("input", {})
                    yield _evt({
                        "type": "tool_start",
                        "name": event["name"],
                        "input": json.dumps(inp, ensure_ascii=False)[:500] if isinstance(inp, dict) else str(inp)[:500],
                    })

                elif kind == "on_tool_end":
                    out = event["data"].get("output", "")
                    out_str = out.content if hasattr(out, "content") else str(out)
                    yield _evt({
                        "type": "tool_end",
                        "name": event["name"],
                        "output": out_str[:1000],
                    })

        except Exception as e:
            yield _evt({"type": "error", "message": str(e)})

        yield _evt({"type": "done"})

    return StreamingResponse(stream(), media_type="text/event-stream")
