# CodexJourney

> 从零构建自主编码 Agent，基于 Harness 理论

## 项目状态

**当前阶段：阶段0 — 最小 Agent（Week 1）**

已实现：
- ReAct 循环
- ToolRegistry（工具注册表）
- Calculator 工具（安全数学计算）
- Time 工具（当前时间/日期）

## 安装

```bash
pip install -e .
```

## 使用

```bash
python -m codex_journey.cli
```

## 阶段路线图

```
阶段0 →  最小Agent（已完成）
阶段1 →  Repo-as-truth（Agent读写仓库）
阶段2 →  质量门禁（Linter + Test Gate）
阶段3 →  Planner-Worker多Agent协作
阶段4 →  Generator-Evaluator对抗
阶段5 →  AGENTS.md人类掌舵体系
阶段6 →  Doc-gardening文档自动维护
```

详见: memory/codex-journey-learning-path.md
