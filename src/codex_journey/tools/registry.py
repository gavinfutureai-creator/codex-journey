"""
ToolRegistry — 工具注册表

核心思想：所有工具注册到这里，Agent 通过统一的 schema 调用。
不需要框架，自己写 50 行搞定。
"""

from typing import Any, Callable


class Tool:
    """单个工具"""

    def __init__(
        self,
        name: str,
        fn: Callable[..., Any],
        description: str,
        parameters: dict,
    ):
        self.name = name
        self.fn = fn
        self.description = description
        self.parameters = parameters

    def call(self, **kwargs) -> str:
        """执行工具，返回字符串结果"""
        try:
            result = self.fn(**kwargs)
            return str(result)
        except Exception as e:
            return f"错误: {e}"


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def register(
        self,
        name: str,
        fn: Callable[..., Any],
        description: str,
        parameters: dict,
    ) -> "ToolRegistry":
        """注册一个工具（链式调用）"""
        self.tools[name] = Tool(name=name, fn=fn, description=description, parameters=parameters)
        return self

    def get(self, name: str) -> Tool | None:
        return self.tools.get(name)

    def get_schema(self) -> list[dict]:
        """返回 OpenAI 格式的 function calling schema"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        **tool.parameters,
                    },
                },
            }
            for tool in self.tools.values()
        ]

    def list_tools(self) -> list[str]:
        """列出所有可用工具"""
        return list(self.tools.keys())

    def invoke(self, name: str, arguments: dict) -> str:
        """调用指定工具"""
        tool = self.get(name)
        if not tool:
            return f"错误: 未知工具 '{name}'"
        return tool.call(**arguments)


def build_default_registry() -> ToolRegistry:
    """构建默认工具注册表（阶段0用）"""
    from codex_journey.tools.calculator import register_calculator_tools
    from codex_journey.tools.time_tools import register_time_tools

    registry = ToolRegistry()
    register_calculator_tools(registry)
    register_time_tools(registry)
    return registry
