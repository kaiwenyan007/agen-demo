from agent.tools.calculator_tool import TOOL_SCHEMA as CALCULATOR_SCHEMA
from agent.tools.calculator_tool import calculate
from agent.tools.datetime_tool import TOOL_SCHEMA as DATETIME_SCHEMA
from agent.tools.datetime_tool import get_current_time
from agent.tools.file_reader import LIST_FILES_SCHEMA, READ_FILE_SCHEMA
from agent.tools.file_reader import list_files, read_file

TOOL_FUNCTIONS = {
    "get_current_time": get_current_time,
    "calculate": calculate,
    "read_file": read_file,
    "list_files": list_files,
}

TOOL_SCHEMAS = [
    DATETIME_SCHEMA,
    CALCULATOR_SCHEMA,
    READ_FILE_SCHEMA,
    LIST_FILES_SCHEMA,
]


def execute_tool(name: str, arguments: dict) -> str:
    fn = TOOL_FUNCTIONS.get(name)
    if not fn:
        return f"未知工具: {name}"
    return str(fn(**arguments))
