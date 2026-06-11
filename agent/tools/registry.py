from agent.tools.calculator_tool import TOOL_SCHEMA as CALCULATOR_SCHEMA
from agent.tools.calculator_tool import calculate
from agent.tools.datetime_tool import TOOL_SCHEMA as DATETIME_SCHEMA
from agent.tools.datetime_tool import get_current_time

TOOL_FUNCTIONS = {
    "get_current_time": get_current_time,
    "calculate": calculate,
}

TOOL_SCHEMAS = [DATETIME_SCHEMA, CALCULATOR_SCHEMA]


def execute_tool(name: str, arguments: dict) -> str:
    fn = TOOL_FUNCTIONS.get(name)
    if not fn:
        return f"未知工具: {name}"
    return str(fn(**arguments))
