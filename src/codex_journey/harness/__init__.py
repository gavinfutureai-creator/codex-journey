"""
Harness 模块 — 多Agent协作框架

包含：
- task.py: 任务定义
- file_lock.py: 文件锁
- coordinator.py: Coordinator Agent
- worker.py: Worker Agent
"""

from codex_journey.harness.task import Task, TaskPlan, TaskType, TaskStatus
from codex_journey.harness.file_lock import FileLock, FileLockContext
from codex_journey.harness.coordinator import CoordinatorAgent
from codex_journey.harness.worker import WorkerAgent


__all__ = [
    "Task",
    "TaskPlan",
    "TaskType",
    "TaskStatus",
    "FileLock",
    "FileLockContext",
    "CoordinatorAgent",
    "WorkerAgent",
]
