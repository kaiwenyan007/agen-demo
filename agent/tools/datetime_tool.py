from datetime import datetime

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "获取当前的日期、时间和星期几。用户问现在几点、今天几号、星期几时必须调用。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

_WEEKDAY_CN = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


def get_current_time() -> str:
    """返回带中文星期的时间字符串，避免 LLM 自行推算星期出错。"""
    now = datetime.now()
    weekday = _WEEKDAY_CN[now.weekday()]
    return (
        f"当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')}，"
        f"今天是{now.year}年{now.month}月{now.day}日，{weekday}。"
        f"（星期几以本工具结果为准：{weekday}）"
    )
