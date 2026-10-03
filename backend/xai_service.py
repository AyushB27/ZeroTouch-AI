"""Optional xAI Responses API client with allowlisted local function execution."""

import json
import os
from typing import Any

import httpx

from backend.enterprise_tools import TOOL_REGISTRY, execute_tool, tool_schemas


class XAIUnavailable(RuntimeError):
    def __init__(self, message: str, executed: list[dict] | None = None):
        super().__init__(message)
        self.executed = executed or []


def _message_text(response: dict) -> str:
    fragments = []
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for block in item.get("content", []):
            if block.get("type") in ("output_text", "text") and block.get("text"):
                fragments.append(block["text"])
    return "\n".join(fragments).strip()


async def run_grok(message: str, context: dict, history: list[dict] | None = None) -> dict:
    """Run one bounded function-call loop. Grok receives tool schemas, never DB access."""
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        raise XAIUnavailable("XAI_API_KEY is not configured")
    model = os.getenv("XAI_MODEL", "grok-4.7")
    endpoint = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1").rstrip("/") + "/responses"
    tools = tool_schemas()
    input_items: Any = [
        {"role": "system", "content": (
            "You are ZeroTouch, an enterprise AI teammate. Use only the registered functions for business data and actions. "
            "Never invent results. Never claim a mutation completed unless the tool result confirms it. "
            "For onboarding, call create_onboarding_plan; it coordinates HR, department training, IT access, Knowledge, and manager tasks. "
            "For failed-payment reports use generate_report. For policy questions use search_knowledge. "
            "Ask a brief follow-up only when required fields are missing. Do not reveal private reasoning. "
            "Return a concise result and next step based on tool output."
        )},
        *[{"role": item["role"], "content": item["content"]}
          for item in (history or [])[-10:] if item.get("role") in ("user", "assistant")],
        {"role": "user", "content": message},
    ]
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    executed: list[dict] = []
    timeout = httpx.Timeout(35.0, connect=8.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(endpoint, headers=headers,
                json={"model": model, "input": input_items, "tools": tools, "tool_choice": "auto"})
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            raise XAIUnavailable(f"xAI request failed: {exc}") from exc

        for _ in range(6):
            calls = [item for item in data.get("output", []) if item.get("type") == "function_call"]
            if not calls:
                return {"reply": _message_text(data), "tool_calls": executed,
                        "provider": "xai", "model": model}
            outputs = []
            for call in calls:
                name = call.get("name", "")
                try:
                    arguments = json.loads(call.get("arguments") or "{}")
                    result = execute_tool(name, arguments, context)
                except Exception as exc:
                    result = {"error": str(exc), "status_code": 422}
                executed.append({"tool": name, "agent": TOOL_REGISTRY.get(name, {}).get("agent", "Supervisor Agent"),
                                 "status": "FAILED" if result.get("error") else "COMPLETED", "result": result})
                outputs.append({"type": "function_call_output", "call_id": call.get("call_id"),
                                "output": json.dumps(result, default=str)})
            try:
                response = await client.post(endpoint, headers=headers,
                    json={"model": model, "input": outputs, "tools": tools,
                          "previous_response_id": data.get("id"), "tool_choice": "auto"})
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                # Avoid replaying successful mutations if only the model summary failed.
                return {"reply": "I ran the requested business tools, but could not finish the AI summary. Review the verified results below.",
                        "tool_calls": executed, "provider": "xai", "model": model,
                        "finalization_error": str(exc)}

    return {"reply": "I reached the safe tool-call limit. The recorded results are available in the task panel.",
            "tool_calls": executed, "provider": "xai", "model": model, "status": "WAITING"}
