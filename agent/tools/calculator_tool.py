TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "calculate",
        "description": "执行基础四则运算（加减乘除），当用户需要做数学计算时使用",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "运算类型：add 加、subtract 减、multiply 乘、divide 除",
                },
                "a": {"type": "number", "description": "第一个操作数"},
                "b": {"type": "number", "description": "第二个操作数"},
            },
            "required": ["operation", "a", "b"],
        },
    },
}


def calculate(operation: str, a: float, b: float) -> str:
    ops = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y,
    }
    fn = ops.get(operation)
    if not fn:
        return f"不支持的运算: {operation}"
    if operation == "divide" and b == 0:
        return "错误：除数不能为 0"
    return str(fn(a, b))
