"""Mock tool executor and noise."""

from __future__ import annotations

from sme_bench.models import ToolCall, ToolEnv, ToolHandlerError, ToolHandlerSpec
from sme_bench.tool_env import MockToolExecutor, with_noise
from tests.unit.conftest import make_task


def test_unknown_tool_returns_error() -> None:
    task = make_task(tool_env=ToolEnv(handlers=[]))
    executor = MockToolExecutor(task)
    result = executor.execute(ToolCall(name="nope", arguments={}))
    assert "error" in result


def test_match_and_once_then_fallback() -> None:
    task = make_task(
        tool_env=ToolEnv(
            noise=False,
            handlers=[
                ToolHandlerSpec(
                    tool="create_booking",
                    once=True,
                    error=ToolHandlerError(status=409, message="room taken"),
                ),
                ToolHandlerSpec(tool="create_booking", response={"id": "bk-2", "status": "ok"}),
            ],
        )
    )
    executor = MockToolExecutor(task)
    first = executor.execute(ToolCall(name="create_booking", arguments={"room": "A"}))
    second = executor.execute(ToolCall(name="create_booking", arguments={"room": "A"}))
    assert first == {"error": "room taken", "status": 409}
    assert second == {"id": "bk-2", "status": "ok"}


def test_noise_is_deterministic() -> None:
    first = with_noise({"qty": 14}, tool_name="get_stock", seed="task-1")
    second = with_noise({"qty": 14}, tool_name="get_stock", seed="task-1")
    assert first == second
    assert first["_meta"]["tool"] == "get_stock"
    assert first["qty"] == 14
