"""
Time Tools — 时间工具

演示简单的只读工具实现。
"""

from datetime import datetime

from codex_journey.tools.registry import ToolRegistry


def get_current_time() -> str:
    """获取当前时间"""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


def get_current_date() -> str:
    """获取当前日期"""
    now = datetime.now()
    return now.strftime("%Y-%m-%d")


def register_time_tools(registry: ToolRegistry) -> None:
    registry.register(
        name="current_time",
        fn=get_current_time,
        description="获取当前时间，格式为 YYYY-MM-DD HH:MM:SS",
        parameters={"type": "object", "properties": {}},
    )

    registry.register(
        name="current_date",
        fn=get_current_date,
        description="获取当前日期，格式为 YYYY-MM-DD",
        parameters={"type": "object", "properties": {}},
    )
