# AGENTS.md

> 这是给 Agent 的新员工手册。
> Agent 不需要记住所有规则，只需要在这里找到方向。
> 当 Agent 犯错时，CI 会拦住它，Agent 根据报错修正。

## 项目概述

- 名称: codex-journey
- 目的: 从零构建自主编码 Agent，基于 Harness 理论
- 技术栈: Python 3.11+, Rich, httpx, OpenAI SDK

## 项目结构

```
codex-journey/
├── src/codex_journey/        # 源代码
│   ├── agent.py              # ReAct 循环核心
│   ├── cli.py                # 命令行入口
│   ├── llm.py                # LLM 调用层（MiniMax/Ollama）
│   ├── tools/                # 工具目录
│   │   ├── registry.py       # 工具注册表
│   │   ├── calculator.py      # 计算器工具（AST安全）
│   │   ├── time_tools.py      # 时间工具
│   │   ├── file_tools.py      # 文件操作工具
│   │   └── quality_tools.py   # 质量门禁工具（Lint + Test）
│   └── harness/              # 多Agent协作框架
│       ├── task.py           # 任务定义
│       ├── file_lock.py      # 文件锁
│       ├── coordinator.py     # Coordinator Agent
│       └── worker.py         # Worker Agent
├── tests/                    # 测试目录
├── AGENTS.md                 # 本文件
├── pyproject.toml            # 项目配置
└── .env.example              # 环境变量模板
```

## 目录索引

- 架构文档: 本文件即为核心架构说明
- 工具说明: 见下方工具列表
- 测试: `pytest tests/`
- Lint: `ruff check .`

## 可用工具

### 基础工具

| 工具名 | 功能 | 重要参数 |
|--------|------|----------|
| `calculator` | 安全数学计算 | `expr`: 表达式字符串 |
| `get_time` | 获取当前时间 | 无 |

### 文件操作工具

| 工具名 | 功能 | 重要参数 |
|--------|------|----------|
| `read_file` | 读取文件 | `path`: 路径, `max_lines`: 最大行数 |
| `write_file` | 写入文件 | `path`: 路径, `content`: 内容 |
| `search_code` | 搜索文件 | `path`: 目录, `pattern`: 关键词 |
| `list_dir` | 列出目录 | `path`: 目录路径 |
| `search_replace` | 查找替换 | `path`, `old_text`, `new_text` |

### 质量门禁工具

| 工具名 | 功能 | 重要参数 |
|--------|------|----------|
| `linter_check` | 运行 ruff 检查代码风格 | `path`: 文件或目录 |
| `linter_fix` | 运行 ruff 自动修复 | `path`: 文件或目录 |
| `pytest_run` | 运行 pytest 测试 | `path`: 测试路径 |
| `run_tests_and_lint` | 综合检查 | `file_path`: 源文件路径 |

## 工具使用规则

### 文件操作

1. **read_file** — 读取文件时，默认最多100行，防止上下文溢出
2. **write_file** — 写入前会自动创建目录，写入后返回字符数
3. **search_code** — 搜索深度遍历，跳过 `.git`, `__pycache__`, `node_modules` 等目录
4. **search_replace** — 必须精确匹配 `old_text`，不支持正则

### 质量门禁（重要）

5. **linter_check** — 每次写完代码必须运行，确保风格正确
6. **pytest_run** — 每次写完测试必须运行，确保测试通过
7. **run_tests_and_lint** — 综合检查，用于验证代码质量

## 多Agent协作（阶段3）

### 架构

```
用户（任务）
    ↓
Coordinator（任务分解 + 审核）
    ↓ 发任务
Worker A（写代码）
Worker B（写测试）
    ↓ 提交结果
Coordinator（审核）
    ↓
通过 → 完成
失败 → 打回重做
```

### 组件

| 组件 | 类型 | 作用 |
|------|------|------|
| `CoordinatorAgent` | Agent | 任务分解 + 结果审核 |
| `WorkerAgent` | Agent | 执行具体子任务 |
| `Task` | 数据类 | 任务定义 |
| `TaskPlan` | 数据类 | 任务计划 |
| `FileLock` | 工具 | 防止并发冲突 |

### 使用方式

```python
from codex_journey.harness import CoordinatorAgent, WorkerAgent, FileLock
from codex_journey.tools.registry import build_default_registry

# 初始化
registry = build_default_registry()
file_lock = FileLock()
worker = WorkerAgent(registry=registry, file_lock=file_lock)
coordinator = CoordinatorAgent(registry=registry)

# 执行任务
plan = coordinator.coordinate("帮我写一个排序模块", worker)
```

## 代码规范

- Python: 使用 ruff 检查代码风格
- 测试: pytest
- 导入顺序: 标准库 → 第三方库 → 本地模块
- 单文件行数: 建议不超过 500 行

## 质量标准

- [x] 所有新工具必须有文档字符串
- [x] read_file 默认限制100行
- [x] 文件操作工具必须处理异常（FileNotFoundError, PermissionError）
- [x] 代码必须通过 ruff 检查
- [x] 测试必须通过 pytest

## 运行方式

```bash
# 安装依赖
pip install -e .

# 安装 lint 工具
pip install ruff pytest

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API key

# 运行 CLI 模式（单 Agent，交互式）
python -m codex_journey.cli

# 运行单 Agent 模式（指定任务）
python -m codex_journey.cli "帮我写一个排序函数"

# 运行多 Agent 协作模式（Coordinator + Worker）
python -m codex_journey.cli "帮我写一个排序函数" --mode multi

# 运行 lint 检查
ruff check .

# 运行测试
pytest tests/
```

## 当前任务

阶段3: Planner-Worker 多Agent
- [x] 实现 task.py - 任务定义
- [x] 实现 file_lock.py - 文件锁
- [x] 实现 coordinator.py - Coordinator Agent
- [x] 实现 worker.py - Worker Agent
- [x] 更新 AGENTS.md
- [x] 改造 cli.py - 添加 --mode multi 支持
- [x] 测试多Agent协作功能
