"""
Coordinator — Coordinator Agent 实现

Coordinator 负责任务分解和结果审核。
"""

import json
import re
from codex_journey.agent import ReactAgent
from codex_journey.tools.registry import ToolRegistry
from codex_journey.llm import create_llm
from codex_journey.harness.task import Task, TaskPlan, TaskType, TaskStatus


class CoordinatorAgent:
    """
    Coordinator Agent：任务分解 + 结果审核

    工作流程：
    1. plan() — 将用户任务分解为子任务列表
    2. review() — 审核 Worker 的执行结果
    3. 协调整个多 Agent 协作流程
    """

    def __init__(
        self,
        llm_provider: str = "minimax",
        registry: ToolRegistry = None,
        show_thought: bool = True,
    ):
        """
        初始化 Coordinator Agent

        Args:
            llm_provider: LLM 提供者
            registry: 工具注册表
            show_thought: 是否显示思考过程
        """
        self.llm = create_llm(provider=llm_provider)
        self.registry = registry or ToolRegistry()
        self.show_thought = show_thought
        self.agent = ReactAgent(
            llm=self.llm,
            registry=self.registry,
            show_thought=show_thought,
        )

    def plan(self, task_description: str) -> TaskPlan:
        """
        将任务分解为子任务

        Args:
            task_description: 原始任务描述

        Returns:
            TaskPlan: 任务计划对象
        """
        if self.show_thought:
            print(f"\n[Coordinator] 分析任务: {task_description}")

        # 构建分解提示
        prompt = f"""将以下任务分解为可执行的子任务：

任务：{task_description}

要求：
1. 代码任务和测试任务要分开
2. 每个子任务只负责一个文件
3. 描述要清晰，便于 Worker 执行
4. file_path 使用完整路径：代码文件如 src/codex_journey/xxx.py，测试文件如 tests/xxx_test.py

输出格式（必须严格遵循，纯 JSON，无任何其他文字）：
{{"tasks": [{{"id": 1, "description": "描述", "task_type": "code", "file_path": "src/codex_journey/xxx.py", "agent": "coder"}}]}}

直接输出 JSON："""

        # 调用 LLM 分解任务
        try:
            result, steps = self.agent.run(prompt)

            # 尝试解析 JSON
            tasks_data = self._parse_json(result)

            if tasks_data and "tasks" in tasks_data:
                tasks = []
                for i, task_data in enumerate(tasks_data["tasks"]):
                    task = Task(
                        id=task_data.get("id", i + 1),
                        description=task_data.get("description", ""),
                        task_type=TaskType(task_data.get("task_type", "code")),
                        file_path=task_data.get("file_path", ""),
                        agent=task_data.get("agent", "coder"),
                    )
                    tasks.append(task)

                plan = TaskPlan(original_task=task_description, tasks=tasks)

                if self.show_thought:
                    print(f"[Coordinator] 分解为 {len(tasks)} 个子任务")
                    print(plan.summary())

                return plan
            else:
                # 解析失败，返回错误信息
                return TaskPlan(
                    original_task=task_description,
                    tasks=[Task(
                        id=1,
                        description=task_description,
                        task_type=TaskType.CODE,
                        file_path="src/task.py",
                        agent="coder",
                    )]
                )

        except Exception as e:
            if self.show_thought:
                print(f"[Coordinator] 任务分解失败: {e}")
            return TaskPlan(
                original_task=task_description,
                tasks=[Task(
                    id=1,
                    description=task_description,
                    task_type=TaskType.CODE,
                    file_path="src/task.py",
                    agent="coder",
                )]
            )

    def review(self, task: Task) -> dict:
        """
        审核任务执行结果

        Args:
            task: 要审核的任务

        Returns:
            审核结果 {"pass": bool, "reason": str}
        """
        if self.show_thought:
            print(f"\n[Coordinator] 审核 Task {task.id}: {task.description}")

        # 构建审核提示
        prompt = f"""审核以下任务执行结果：

任务 ID: {task.id}
任务类型: {task.task_type.value}
任务描述: {task.description}
目标文件: {task.file_path}

执行结果：
{task.result or "无结果"}

请严格审核以下方面：
1. 是否完成了任务描述的要求？
2. 代码是否合理，没有明显错误？
3. 是否通过了 lint 检查？
4. 测试用例是否充分？

返回格式（必须严格遵循，纯 JSON，无任何其他文字）：
{{"pass": true, "reason": "通过原因"}}
或
{{"pass": false, "reason": "拒绝原因", "suggestions": ["建议1", "建议2"]}}

直接输出 JSON："""

        # 调用 LLM 审核
        try:
            result, steps = self.agent.run(prompt)

            # 尝试解析 JSON
            review_result = self._parse_json(result)

            if review_result and "pass" in review_result:
                if review_result["pass"]:
                    task.mark_approved()
                else:
                    task.mark_rejected(review_result.get("reason", "审核未通过"))
                return review_result

            # JSON 解析失败，尝试从文本识别
            text_result = self._parse_review_from_text(result)
            if text_result:
                if text_result["pass"]:
                    task.mark_approved()
                else:
                    task.mark_rejected(text_result.get("reason", "文本审核未通过"))
                return text_result

            # 解析完全失败，尝试从 task.result 中推断
            # 检查实际生成的文件是否存在
            inference = self._infer_review_from_task(task)
            if inference:
                if inference["pass"]:
                    task.mark_approved()
                else:
                    task.mark_rejected(inference.get("reason", "无法确定审核结果"))
                return inference

            # 解析失败，保守返回不通过
            task.mark_rejected("审核结果解析失败")
            return {"pass": False, "reason": "审核结果解析失败"}

        except Exception as e:
            error_msg = f"审核异常: {e}"
            task.mark_rejected(error_msg)
            return {"pass": False, "reason": error_msg}

    def _parse_json(self, text: str) -> dict:
        """
        从文本中提取 JSON

        Args:
            text: 包含 JSON 的文本

        Returns:
            解析后的字典，解析失败返回 None
        """
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试从 markdown 代码块中提取
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试找第一个 { 并匹配到对应的 }
        start = text.find("{")
        if start != -1:
            depth = 0
            for i, ch in enumerate(text[start:], start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i + 1])
                        except json.JSONDecodeError:
                            break
                        break

        return None

    def _parse_review_from_text(self, text: str) -> dict | None:
        """
        从非 JSON 格式的审核文本中提取结果

        Args:
            text: 审核响应文本

        Returns:
            {"pass": bool, "reason": str} 或 None
        """
        if not text:
            return None

        text_lower = text.lower()

        # 判断是否通过
        pass_indicators = [
            "审核通过", "通过审核", "pass", "approved",
            "任务完成", "执行完成", "符合要求", "满足要求",
        ]
        fail_indicators = [
            "审核拒绝", "拒绝", "failed", "rejected",
            "未完成", "不通过", "不符合", "不满足",
        ]

        pass_score = sum(1 for indicator in pass_indicators if indicator in text_lower)
        fail_score = sum(1 for indicator in fail_indicators if indicator in text_lower)

        if pass_score > 0 and pass_score >= fail_score:
            # 提取简短理由
            reason_lines = []
            for line in text.split("\n"):
                stripped = line.strip()
                if stripped and len(stripped) > 5:
                    reason_lines.append(stripped)
                    if len(reason_lines) >= 2:
                        break
            reason = " ".join(reason_lines)[:200] if reason_lines else "文本审核通过"
            return {"pass": True, "reason": reason}
        elif fail_score > 0:
            reason_lines = []
            for line in text.split("\n"):
                stripped = line.strip()
                if stripped and len(stripped) > 5:
                    reason_lines.append(stripped)
                    if len(reason_lines) >= 2:
                        break
            reason = " ".join(reason_lines)[:200] if reason_lines else "文本审核拒绝"
            return {"pass": False, "reason": reason}

        return None

    def _infer_review_from_task(self, task) -> dict | None:
        """
        根据 task.result 中的执行结果推断审核结果

        当 JSON 和文本解析都失败时，作为兜底判断。
        主要通过检查 task.result 中是否包含成功创建文件等信息来推断。

        Args:
            task: 任务对象

        Returns:
            {"pass": bool, "reason": str} 或 None
        """
        import os

        # 对于 code 和 test 任务，优先检查文件是否实际创建
        file_path = task.file_path
        if file_path and os.path.exists(file_path):
            return {"pass": True, "reason": f"文件 {file_path} 已创建"}

        # 文件不存在，检查 result 中是否有失败指示
        if task.result:
            result_lower = task.result.lower()
            failure_indicators = [
                "错误", "失败", "不存在", "failed",
                "rejected", "拒绝", "异常",
                "error:", "failed:",
            ]
            failure_count = sum(1 for i in failure_indicators if i in result_lower)
            if failure_count > 0:
                return {"pass": False, "reason": "执行结果包含错误信息"}

        return None

    def coordinate(self, task_description: str, worker) -> TaskPlan:
        """
        协调整个任务执行流程

        Args:
            task_description: 原始任务描述
            worker: Worker Agent 实例

        Returns:
            最终的任务计划（包含所有子任务的状态）
        """
        # 1. 分解任务
        plan = self.plan(task_description)

        # 2. 按顺序执行任务
        for task in plan.tasks:
            if self.show_thought:
                print(f"\n{'='*50}")
                print(f"[Coordinator] 开始执行 Task {task.id}")

            # Worker 执行
            result = worker.execute_with_retry(task)

            # 标记为审核中
            task.mark_reviewing()

            # 3. Coordinator 审核
            review_result = self.review(task)

            if self.show_thought:
                if review_result["pass"]:
                    print(f"[Coordinator] Task {task.id} 审核通过 ✓")
                else:
                    print(f"[Coordinator] Task {task.id} 审核拒绝: {review_result.get('reason')}")

        # 4. 输出总结
        if self.show_thought:
            print(f"\n{'='*50}")
            print("[Coordinator] 任务执行完成")
            print(plan.summary())

        return plan
