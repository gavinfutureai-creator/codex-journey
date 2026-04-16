"""
Calculator Tools — 计算器工具

演示最简单的工具实现：安全地执行数学计算。
"""

from codex_journey.tools.registry import ToolRegistry


def calculate(expr: str) -> str:
    """
    执行数学计算（安全版本）

    只支持基本运算：+ - * / ** () 和三角/对数函数。
    使用 ast.literal_eval 做安全检查。
    """
    import ast
    import operator
    import math

    # 支持的运算和函数
    safe_math = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "pow": pow,
    }

    safe_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    safe_names = {**{k: getattr(math, k) for k in dir(math) if not k.startswith("_")}, **safe_math}

    def safe_eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp) and type(node.op) in safe_ops:
            return safe_ops[type(node.op)](safe_eval(node.left), safe_eval(node.right))
        elif isinstance(node, ast.UnaryOp) and type(node.op) in safe_ops:
            return safe_ops[type(node.op)](safe_eval(node.operand))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in safe_names:
            args = [safe_eval(arg) for arg in node.args]
            return safe_names[node.func.id](*args)
        elif isinstance(node, ast.Name):
            if node.id in safe_names:
                return safe_names[node.id]
            raise ValueError(f"不支持的变量: {node.id}")
        else:
            raise ValueError(f"不支持的表达式: {ast.dump(node)}")

    try:
        tree = ast.parse(expr.strip(), mode="eval")
        result = safe_eval(tree.body)
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"


def register_calculator_tools(registry: ToolRegistry) -> None:
    registry.register(
        name="calculator",
        fn=calculate,
        description="执行数学计算。支持: +, -, *, /, **, 括号, abs, round, min, max, sum, pow, 以及所有 math 模块函数如 sin, cos, log, sqrt 等。",
        parameters={
            "properties": {
                "expr": {
                    "type": "string",
                    "description": "数学表达式，例如 '2+3*4' 或 'sqrt(16) + sin(3.14/2)'",
                }
            },
            "required": ["expr"],
        },
    )
