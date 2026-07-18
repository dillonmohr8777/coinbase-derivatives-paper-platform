"""Agent core — provider-agnostic LLM + tool calling ('Skills'). Shared by bot & radar.

The videos cite GPT-5.6 / Claude Fable-5 / 'Skills'. Build against the interface below so any
tool-calling model drops in. A MockLLM ships so everything runs with no keys.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Callable, Protocol

# --- Tool registry ("Skills") -------------------------------------------------
_TOOLS: dict[str, "Tool"] = {}


@dataclass
class Tool:
    name: str
    description: str
    fn: Callable[..., Any]
    schema: dict = field(default_factory=dict)  # JSON schema of args, for the LLM


def tool(name: str, description: str, schema: dict | None = None):
    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        _TOOLS[name] = Tool(name=name, description=description, fn=fn, schema=schema or {})
        return fn
    return deco


def get_tools() -> dict[str, Tool]:
    return dict(_TOOLS)


# --- LLM client interface -----------------------------------------------------
class LLMClient(Protocol):
    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """Return {'text': str, 'tool_calls': [{'name': str, 'args': dict}, ...]}."""
        ...


class MockLLM:
    """Deterministic stand-in: no network. Lets tests/`make run` work with no keys."""

    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        return {"text": "[mock] no live model configured", "tool_calls": []}


def get_llm(settings) -> LLMClient:
    if settings.llm_provider == "mock":
        return MockLLM()
    # TODO(codex): OpenAIClient / AnthropicClient adapters implementing LLMClient.
    #              Verify current model ids at build time. Never hard-code keys.
    raise NotImplementedError(f"LLM provider '{settings.llm_provider}' not implemented")


@dataclass
class AgentResult:
    text: str
    tool_calls: list[dict] = field(default_factory=list)
    log: list[str] = field(default_factory=list)


class Agent:
    """Minimal tool-calling loop. Decomposes a task, calls Skills, narrates the run log."""

    def __init__(self, llm: LLMClient, tools: dict[str, Tool] | None = None) -> None:
        self.llm = llm
        self.tools = tools or get_tools()

    def run(self, task: str, max_steps: int = 6) -> AgentResult:
        messages = [{"role": "user", "content": task}]
        log = [f"task: {task}"]
        calls_seen: list[dict] = []
        specs = [
            {"name": t.name, "description": t.description, "parameters": t.schema}
            for t in self.tools.values()
        ]
        final_text = ""
        for _ in range(max_steps):
            out = self.llm.complete(messages, tools=specs)
            final_text = str(out.get("text", ""))
            calls = out.get("tool_calls", [])
            if final_text:
                log.append(final_text)
            if not calls:
                break
            messages.append({"role": "assistant", "content": final_text, "tool_calls": calls})
            for call in calls:
                name, args = call.get("name"), call.get("args", {})
                if name not in self.tools:
                    result: Any = {"error": f"unknown tool: {name}"}
                else:
                    try:
                        result = self.tools[name].fn(**args)
                    except Exception as exc:
                        result = {"error": type(exc).__name__, "detail": str(exc)}
                calls_seen.append(call)
                log.append(f"tool:{name} -> {result}")
                messages.append(
                    {"role": "tool", "name": name, "content": json.dumps(result, default=str)}
                )
        else:
            log.append(f"halted after max_steps={max_steps}")
        return AgentResult(text=final_text, tool_calls=calls_seen, log=log)
