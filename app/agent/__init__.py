"""Agent core — provider-agnostic LLM + tool calling ('Skills'). Shared by bot & radar.

The videos cite GPT-5.6 / Claude Fable-5 / 'Skills'. Build against the interface below so any
tool-calling model drops in. A MockLLM ships so everything runs with no keys.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
        # TODO(codex): real loop — ask LLM, execute returned tool_calls against self.tools,
        #              feed results back, repeat until done or max_steps. Append each step to
        #              `log` (this becomes the dashboard run log). MockLLM returns no calls,
        #              so this base impl just echoes.
        out = self.llm.complete([{"role": "user", "content": task}])
        return AgentResult(text=out["text"], tool_calls=out.get("tool_calls", []),
                           log=[f"task: {task}", out["text"]])
