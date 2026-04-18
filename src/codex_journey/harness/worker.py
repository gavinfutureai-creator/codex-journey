"""
Worker — Worker Agent 实现

Worker 负责任务的具体执行。
"""

from codex_journey.agent import ReactAgent
from codex_journey.tools.registry import ToolRegistry
from codex_journey.llm import create_llm
from codex_journey.harness.task import Task, TaskStatus
from codex_journey.harness.file_lock import FileLock


class WorkerAgent:
    """
    Worker Agent：执行具体的子任务

    工作流程：
    1. 接收任务
    2. 检查文件锁
    3. 执行任务（调用 ReactAgent）
    4. 运行 Linter 检查
    5. 运行 Test 检查
    6. 释放文件锁
    7. 返回结果
    """

    def __init__(
        self,
        llm_provider: str = "minimax",
        registry: ToolRegistry = None,
        file_lock: FileLock = None,
        show_thought: bool = True,
    ):
        """
        初始化 Worker Agent

        Args:
            llm_provider: LLM 提供者
            registry: 工具注册表
            file_lock: 文件锁
            show_thought: 是否显示思考过程
        """
        self.llm = create_llm(provider=llm_provider)
        self.registry = registry or ToolRegistry()
        self.file_lock = file_lock or FileLock()
        self.show_thought = show_thought
        self.agent = ReactAgent(
            llm=self.llm,
            registry=self.registry,
            show_thought=show_thought,
            max_turns=30,
        )

    def execute(self, task: Task) -> dict:
        """
        执行任务

        Args:
            task: 要执行的任务

        Returns:
            执行结果 {"success": bool, "output": str, "error": str}
        """
        task.mark_in_progress()

        # 检查文件锁
        if not self.file_lock.acquire(task.file_path):
            return {
                "success": False,
                "output": None,
                "error": f"无法获取文件锁: {task.file_path}",
            }

        try:
            # 构建任务提示
            prompt = self._build_task_prompt(task)

            # 执行任务
            if self.show_thought:
                print(f"\n[Worker] 开始执行 Task {task.id}: {task.description}")

            answer, steps = self.agent.run(prompt)

            # 检查是否有严重错误
            if "错误" in answer or "失败" in answer:
                task.mark_failed(answer)
                return {
                    "success": False,
                    "output": answer,
                    "error": "任务执行失败",
                }

            # 任务完成
            task.mark_completed(answer)

            if self.show_thought:
                print(f"[Worker] Task {task.id} 执行完成")

            return {
                "success": True,
                "output": answer,
                "error": None,
            }

        except Exception as e:
            error_msg = f"执行异常: {str(e)}"
            task.mark_failed(error_msg)
            return {
                "success": False,
                "output": None,
                "error": error_msg,
            }

        finally:
            # 释放文件锁
            self.file_lock.release(task.file_path)

    def _build_task_prompt(self, task: Task) -> str:
        """
        构建任务提示

        Args:
            task: 任务对象

        Returns:
            任务提示文本
        """
        base_prompt = f"""你是一个专业的程序员，负责执行以下任务：

任务类型: {task.task_type.value}
任务描述: {task.description}
目标文件: {task.file_path}

请按照以下步骤执行：

1. 如果目标文件已存在，先读取现有内容了解上下文
2. 根据任务描述生成代码
3. 使用 write_file 工具写入目标文件
4. 使用 linter_check 工具检查代码风格
5. 如果有风格问题，尝试使用 linter_fix 自动修复
6. 如果是测试任务，使用 pytest_run 运行测试
7. 确保所有检查通过后再报告完成

重要：
- 如果遇到问题不要放弃，尝试不同的方法
- 代码质量很重要，必须通过 lint 检查
- 测试必须通过才能算完成任务完成
"""

        # 根据任务类型添加特定提示
        if task.task_type.value == "test":
            base_prompt += """
- 测试文件路径: tests/ 目录下
- 导入被测试模块时使用相对导入
- 不要 import 未使用的模块（如 pytest 如果没有用到 @pytest.mark 等）
- 确保测试覆盖率合理
"""
        elif task.task_type.value == "code":
            base_prompt += """
- 项目根目录是当前目录，代码放在 src/codex_journey/ 目录下
- 不要修改任何已存在的文件（如 __init__.py）
- 遵循项目的代码规范
- 添加必要的文档字符串
"""

        return base_prompt

    def execute_with_retry(self, task: Task, max_attempts: int = 3) -> dict:
        """
        带重试的任务执行

        Args:
            task: 要执行的任务
            max_attempts: 最大尝试次数

        Returns:
            执行结果
        """
        for attempt in range(1, max_attempts + 1):
            if self.show_thought:
                print(f"[Worker] Task {task.id} 尝试 {attempt}/{max_attempts}")

            result = self.execute(task)

            if result["success"]:
                return result

            # 如果失败，检查是否可以重试
            if attempt < max_attempts:
                task.status = TaskStatus.PENDING  # 重置状态允许重试
                if self.show_thought:
                    print(f"[Worker] Task {task.id} 失败，准备重试: {result['error']}")
            else:
                if self.show_thought:
                    print(f"[Worker] Task {task.id} 已达最大尝试次数")

        return result
