"""
File Tools — 文件操作工具

提供基础的仓库读写能力，支持：
- 读取文件内容
- 写入文件内容
- 搜索文件内容
- 列出目录结构
"""

import os
import re
from codex_journey.tools.registry import ToolRegistry


def read_file(path: str, max_lines: int = 100) -> str:
    """
    读取文件内容

    Args:
        path: 文件路径
        max_lines: 最大读取行数，默认100行，防止上下文溢出

    Returns:
        文件内容字符串
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if len(lines) > max_lines:
            content = "".join(lines[:max_lines])
            return f"{content}\n... (共 {len(lines)} 行，仅显示前 {max_lines} 行)"
        return "".join(lines)
    except FileNotFoundError:
        return f"错误: 文件不存在 '{path}'"
    except PermissionError:
        return f"错误: 无权访问 '{path}'"
    except Exception as e:
        return f"错误: {e}"


def write_file(path: str, content: str) -> str:
    """
    写入内容到文件

    Args:
        path: 文件路径
        content: 要写入的内容

    Returns:
        操作结果
    """
    try:
        # 确保目录存在
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"已写入 {path} ({len(content)} 字符)"
    except PermissionError:
        return f"错误: 无权写入 '{path}'"
    except Exception as e:
        return f"错误: {e}"


def search_code(path: str, pattern: str, file_patterns: list[str] | None = None) -> str:
    """
    在指定目录中搜索包含关键词的文件

    Args:
        path: 搜索的根目录
        pattern: 要搜索的关键词
        file_patterns: 匹配的文件类型，如 ['.py', '.md']，默认 py/md/yaml/json/txt

    Returns:
        匹配的文件列表
    """
    if file_patterns is None:
        file_patterns = [".py", ".md", ".yaml", ".yml", ".json", ".txt", ".toml"]

    matches = []
    pattern_lower = pattern.lower()

    try:
        for root, dirs, files in os.walk(path):
            # 跳过隐藏目录和特殊目录
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "node_modules", ".git", "venv", ".venv")]

            for f in files:
                # 检查文件类型
                if not any(f.endswith(ext) for ext in file_patterns):
                    continue

                full_path = os.path.join(root, f)

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as file:
                        content = file.read()
                        if pattern_lower in content.lower():
                            # 计算匹配次数
                            count = content.lower().count(pattern_lower)
                            rel_path = os.path.relpath(full_path, path)
                            matches.append(f"{rel_path} (匹配 {count} 次)")
                except Exception:
                    continue

        if not matches:
            return f"未找到包含 '{pattern}' 的文件"

        return "\n".join(matches[:20])  # 最多返回20个结果
    except Exception as e:
        return f"错误: {e}"


def list_dir(path: str = ".") -> str:
    """
    列出目录内容

    Args:
        path: 目录路径，默认当前目录

    Returns:
        目录内容列表
    """
    try:
        entries = os.listdir(path)
        entries.sort()

        result = []
        for entry in entries:
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                result.append(f"📁 {entry}/")
            else:
                size = os.path.getsize(full_path)
                result.append(f"📄 {entry} ({size} bytes)")

        return "\n".join(result)
    except FileNotFoundError:
        return f"错误: 目录不存在 '{path}'"
    except PermissionError:
        return f"错误: 无权访问 '{path}'"
    except Exception as e:
        return f"错误: {e}"


def search_replace(path: str, old_text: str, new_text: str) -> str:
    """
    在文件中查找并替换文本

    Args:
        path: 文件路径
        old_text: 要替换的文本
        new_text: 替换后的文本

    Returns:
        操作结果
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if old_text not in content:
            return f"错误: 未找到要替换的文本"

        new_content = content.replace(old_text, new_text)

        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        count = content.count(old_text)
        return f"已替换 {path} ({count} 处)"
    except FileNotFoundError:
        return f"错误: 文件不存在 '{path}'"
    except Exception as e:
        return f"错误: {e}"


def register_file_tools(registry: ToolRegistry) -> None:
    """注册文件操作工具"""
    registry.register(
        name="read_file",
        fn=read_file,
        description="读取文件内容。支持指定最大行数防止上下文溢出。",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径",
                },
                "max_lines": {
                    "type": "integer",
                    "description": "最大读取行数，默认100行",
                    "default": 100,
                },
            },
            "required": ["path"],
        },
    )

    registry.register(
        name="write_file",
        fn=write_file,
        description="写入内容到文件。如果文件或目录不存在，会自动创建。",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径",
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容",
                },
            },
            "required": ["path", "content"],
        },
    )

    registry.register(
        name="search_code",
        fn=search_code,
        description="在目录中搜索包含关键词的文件。支持 .py, .md, .yaml, .json 等格式。",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "搜索的根目录路径",
                },
                "pattern": {
                    "type": "string",
                    "description": "要搜索的关键词",
                },
                "file_patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "匹配的文件扩展名，默认 ['.py', '.md', '.yaml', '.json']",
                },
            },
            "required": ["path", "pattern"],
        },
    )

    registry.register(
        name="list_dir",
        fn=list_dir,
        description="列出目录内容和文件大小。显示 📁 表示文件夹，📄 表示文件。",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "目录路径，默认当前目录 '.'",
                    "default": ".",
                },
            },
        },
    )

    registry.register(
        name="search_replace",
        fn=search_replace,
        description="在文件中查找并替换文本。用于代码重构或修复。",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径",
                },
                "old_text": {
                    "type": "string",
                    "description": "要替换的文本（必须精确匹配）",
                },
                "new_text": {
                    "type": "string",
                    "description": "替换后的文本",
                },
            },
            "required": ["path", "old_text", "new_text"],
        },
    )
