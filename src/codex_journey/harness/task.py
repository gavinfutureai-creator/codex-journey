"""
Task — 任务定义

定义多Agent协作中的任务结构。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"      # 待执行
    IN_PROGRESS = "in_progress"  # 执行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"        # 失败
    REVIEWING = "reviewing"   # 审核中
    APPROVED = "approved"     # 审核通过
    REJECTED = "rejected"    # 审核拒绝


class TaskType(Enum):
    """任务类型"""
    CODE = "code"           # 写代码
    TEST = "test"           # 写测试
    REFACTOR = "refactor"   # 重构
    FIX = "fix"             # 修复bug
    DOC = "doc"             # 写文档


@dataclass
class Task:
    """任务定义"""
    id: int
    description: str
    task_type: TaskType
    file_path: str
    agent: str  # "coder" 或 "tester"
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None  # 执行结果
    review_result: Optional[dict] = None  # 审核结果 {"pass": bool, "reason": str}
    attempts: int = 0  # 尝试次数
    max_attempts: int = 3  # 最大尝试次数

    def mark_in_progress(self):
        """标记为执行中"""
        self.status = TaskStatus.IN_PROGRESS
        self.attempts += 1

    def mark_completed(self, result: str):
        """标记为完成"""
        self.status = TaskStatus.COMPLETED
        self.result = result

    def mark_failed(self, error: str):
        """标记为失败"""
        self.status = TaskStatus.FAILED
        self.result = error

    def mark_reviewing(self):
        """标记为审核中"""
        self.status = TaskStatus.REVIEWING

    def mark_approved(self):
        """标记为审核通过"""
        self.status = TaskStatus.APPROVED

    def mark_rejected(self, reason: str):
        """标记为审核拒绝"""
        self.status = TaskStatus.REJECTED
        self.review_result = {"pass": False, "reason": reason}

    def can_retry(self) -> bool:
        """是否可以重试"""
        return self.attempts < self.max_attempts and self.status == TaskStatus.REJECTED

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "description": self.description,
            "task_type": self.task_type.value,
            "file_path": self.file_path,
            "agent": self.agent,
            "status": self.status.value,
            "result": self.result,
            "review_result": self.review_result,
            "attempts": self.attempts,
        }


@dataclass
class TaskPlan:
    """任务计划（包含多个子任务）"""
    original_task: str  # 原始任务描述
    tasks: list[Task]
    created_at: str = ""

    def get_pending_tasks(self) -> list[Task]:
        """获取待执行的任务"""
        return [t for t in self.tasks if t.status == TaskStatus.PENDING]

    def get_in_progress_tasks(self) -> list[Task]:
        """获取执行中的任务"""
        return [t for t in self.tasks if t.status == TaskStatus.IN_PROGRESS]

    def get_completed_tasks(self) -> list[Task]:
        """获取已完成的任务"""
        return [t for t in self.tasks if t.status == TaskStatus.COMPLETED]

    def get_approved_tasks(self) -> list[Task]:
        """获取审核通过的任务"""
        return [t for t in self.tasks if t.status == TaskStatus.APPROVED]

    def get_rejected_tasks(self) -> list[Task]:
        """获取审核拒绝的任务"""
        return [t for t in self.tasks if t.status == TaskStatus.REJECTED]

    def all_approved(self) -> bool:
        """是否所有任务都审核通过"""
        return all(t.status == TaskStatus.APPROVED for t in self.tasks)

    def has_pending(self) -> bool:
        """是否有待执行的任务"""
        return any(t.status == TaskStatus.PENDING for t in self.tasks)

    def summary(self) -> str:
        """生成任务摘要"""
        lines = [f"任务计划（共 {len(self.tasks)} 个子任务）:", f"原始任务: {self.original_task}", ""]

        for t in self.tasks:
            status_icon = {
                TaskStatus.PENDING: "⏳",
                TaskStatus.IN_PROGRESS: "🔄",
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
                TaskStatus.REVIEWING: "👀",
                TaskStatus.APPROVED: "👍",
                TaskStatus.REJECTED: "👎",
            }.get(t.status, "❓")

            lines.append(f"{status_icon} Task {t.id}: [{t.task_type.value}] {t.description}")
            lines.append(f"   文件: {t.file_path} | Agent: {t.agent}")
            if t.result:
                lines.append(f"   结果: {t.result[:100]}...")
            if t.review_result:
                lines.append(f"   审核: {'通过' if t.review_result.get('pass') else '拒绝'} - {t.review_result.get('reason', '')}")
            lines.append("")

        return "\n".join(lines)
