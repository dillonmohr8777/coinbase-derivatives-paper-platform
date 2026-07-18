from app.agent import Agent, Tool


class ToolCallingLLM:
    def __init__(self):
        self.calls = 0

    def complete(self, messages, tools=None):
        self.calls += 1
        if self.calls == 1:
            return {"text": "checking", "tool_calls": [{"name": "price", "args": {"symbol": "BTC-PERP"}}]}
        return {"text": "done", "tool_calls": []}


def test_agent_executes_tool_and_feeds_result_back():
    llm = ToolCallingLLM()
    agent = Agent(llm, {"price": Tool("price", "price lookup", lambda symbol: {"symbol": symbol, "price": 100})})
    result = agent.run("analyze")
    assert result.text == "done"
    assert result.tool_calls[0]["name"] == "price"
    assert any("BTC-PERP" in line for line in result.log)
