"""Input fingerprint stability across new optional fields."""

from __future__ import annotations

from sme_bench.fingerprints import task_input_fingerprint
from sme_bench.models import ToolEnv, ToolHandlerSpec, ToolSpec
from tests.unit.conftest import make_task


def test_empty_tools_do_not_change_fingerprint() -> None:
    base = make_task()
    with_defaults = make_task(tools=[], tool_choice="auto")
    assert task_input_fingerprint(base) == task_input_fingerprint(with_defaults)


def test_tools_change_fingerprint() -> None:
    base = make_task()
    with_tool = make_task(tools=[ToolSpec(name="get_stock", description="x")])
    assert task_input_fingerprint(base) != task_input_fingerprint(with_tool)


def test_empty_tool_env_does_not_change_fingerprint() -> None:
    base = make_task()
    with_defaults = make_task(tool_env=ToolEnv())
    assert task_input_fingerprint(base) == task_input_fingerprint(with_defaults)


def test_tool_env_handlers_change_fingerprint() -> None:
    base = make_task()
    with_env = make_task(
        tool_env=ToolEnv(handlers=[ToolHandlerSpec(tool="get_stock", response={"qty": 14})])
    )
    assert task_input_fingerprint(base) != task_input_fingerprint(with_env)
