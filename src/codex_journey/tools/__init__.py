"""Tools 模块"""

from codex_journey.tools.calculator import register_calculator_tools
from codex_journey.tools.time_tools import register_time_tools
from codex_journey.tools.file_tools import register_file_tools


def register_all_tools(registry):
    """注册所有工具到注册表"""
    register_calculator_tools(registry)
    register_time_tools(registry)
    register_file_tools(registry)
