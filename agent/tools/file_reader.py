from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "读取项目内指定相对路径的文本文件内容",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "相对于项目根目录的文件路径，如 knowledge/project-intro.md",
                },
            },
            "required": ["path"],
        },
    },
}

LIST_FILES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": "列出指定目录下的文件（不含子目录内容详情）",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "相对路径目录，如 knowledge 或 .",
                },
            },
            "required": ["path"],
        },
    },
}


def read_file(path: str) -> str:
    target = (PROJECT_ROOT / path).resolve()
    if not str(target).startswith(str(PROJECT_ROOT)):
        return "错误：不允许访问项目目录外的文件"
    if not target.exists():
        return f"错误：文件不存在 {path}"
    return target.read_text(encoding="utf-8")[:8000]


def list_files(path: str = ".") -> str:
    target = (PROJECT_ROOT / path).resolve()
    if not str(target).startswith(str(PROJECT_ROOT)):
        return "错误：不允许访问项目目录外的路径"
    if not target.is_dir():
        return f"错误：目录不存在 {path}"
    files = [f.name for f in target.iterdir()]
    return ", ".join(files) if files else "（空目录）"
