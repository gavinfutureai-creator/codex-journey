"""
Quality Tools — 质量门禁工具

提供代码质量检查工具：
- linter_check: 运行 ruff 检查代码风格
- pytest_run: 运行 pytest 执行测试
"""

import subprocess
from codex_journey.tools.registry import ToolRegistry


def run_command(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    """
    运行命令并返回结果

    Args:
        cmd: 命令列表
        timeout: 超时时间（秒）

    Returns:
        (返回码, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"命令执行超时（{timeout}秒）"
    except FileNotFoundError:
        return -1, "", f"命令不存在: {cmd[0]}"
    except Exception as e:
        return -1, "", f"执行错误: {e}"


def linter_check(path: str = ".") -> str:
    """
    运行 ruff 检查代码风格

    Args:
        path: 文件或目录路径，默认当前目录

    Returns:
        检查结果
    """
    returncode, stdout, stderr = run_command(["ruff", "check", path])

    if returncode == 0:
        return f"✅ {path}: ruff 检查通过，无错误"

    output = stdout or stderr
    if not output:
        return f"❌ {path}: ruff 检查失败（返回码 {returncode}）"

    # 限制输出长度
    lines = output.strip().split("\n")
    if len(lines) > 30:
        output = "\n".join(lines[:30]) + f"\n... (共 {len(lines)} 行错误)"

    return f"❌ {path}: ruff 检查失败\n\n{output}"


def linter_fix(path: str = ".") -> str:
    """
    运行 ruff 自动修复代码风格问题

    Args:
        path: 文件或目录路径，默认当前目录

    Returns:
        修复结果
    """
    returncode, stdout, stderr = run_command(["ruff", "check", "--fix", path])

    if returncode == 0:
        return f"✅ {path}: ruff 自动修复完成，无问题"

    output = stdout or stderr
    if "fixed" in output.lower():
        # 提取修复数量
        for line in output.split("\n"):
            if "fixed" in line.lower():
                return f"✅ {path}: {line.strip()}"

    return f"⚠️ {path}: 自动修复完成，但仍有剩余问题\n\n{output[:500]}"


def pytest_run(path: str = "tests/", verbose: bool = True) -> str:
    """
    运行 pytest 执行测试

    Args:
        path: 测试文件或目录路径，默认 tests/
        verbose: 是否显示详细输出

    Returns:
        测试结果
    """
    cmd = ["pytest", path]
    if verbose:
        cmd.append("-v")

    returncode, stdout, stderr = run_command(cmd, timeout=120)

    output = stdout + stderr

    if returncode == 0:
        # 提取测试统计
        for line in output.split("\n"):
            if "passed" in line.lower() or "passed" in line.lower():
                return f"✅ {path}: {line.strip()}"
        return f"✅ {path}: pytest 通过"

    # 解析失败信息
    error_lines = []
    in_error = False
    for line in output.split("\n"):
        if "FAILED" in line or "ERROR" in line:
            in_error = True
        if in_error and line.strip():
            error_lines.append(line)
            if len(error_lines) > 20:
                break

    error_msg = "\n".join(error_lines) if error_lines else output[:500]

    return f"❌ {path}: pytest 失败\n\n{error_msg}"


def run_tests_and_lint(file_path: str) -> str:
    """
    依次运行 lint 和 test

    Args:
        file_path: 要检查的文件路径

    Returns:
        综合结果
    """
    # 先 lint
    lint_result = linter_check(file_path)

    # 再 test
    test_path = file_path.replace("src/", "tests/")
    if not test_path.endswith("_test.py"):
        test_path = test_path.replace(".py", "_test.py")
    test_result = pytest_run(test_path)

    return f"## Lint 检查\n{lint_result}\n\n## 测试检查\n{test_result}"


def register_quality_tools(registry: ToolRegistry) -> None:
    """注册质量门禁工具"""
    registry.register(
        name="linter_check",
        fn=linter_check,
        description="运行 ruff 检查代码风格。返回检查结果，0错误表示通过。",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件或目录路径，默认当前目录 '.'",
                    "default": ".",
                },
            },
        },
    )

    registry.register(
        name="linter_fix",
        fn=linter_fix,
        description="运行 ruff 自动修复代码风格问题。",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件或目录路径，默认当前目录 '.'",
                    "default": ".",
                },
            },
        },
    )

    registry.register(
        name="pytest_run",
        fn=pytest_run,
        description="运行 pytest 执行测试。返回测试结果，通过或失败。",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "测试文件或目录路径，默认 'tests/'",
                    "default": "tests/",
                },
                "verbose": {
                    "type": "boolean",
                    "description": "是否显示详细输出，默认 true",
                    "default": True,
                },
            },
        },
    )

    registry.register(
        name="run_tests_and_lint",
        fn=run_tests_and_lint,
        description="依次运行 lint 检查和 pytest 测试。用于验证代码质量。",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "源文件路径，测试文件会自动推断",
                },
            },
            "required": ["file_path"],
        },
    )
