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
│   │   └── file_tools.py      # 文件操作工具
│   └── harness/              # Harness 框架（待实现）
├── tests/                    # 测试目录
├── AGENTS.md                 # 本文件
├── pyproject.toml            # 项目配置
└── .env.example              # 环境变量模板
```

## 目录索引

- 架构文档: 本文件即为核心架构说明
- 工具说明: 见下方工具列表
- 测试: `pytest tests/`

## 可用工具

| 工具名 | 功能 | 重要参数 |
|--------|------|----------|
| `calculator` | 安全数学计算 | `expr`: 表达式字符串 |
| `get_time` | 获取当前时间 | 无 |
| `read_file` | 读取文件 | `path`: 路径, `max_lines`: 最大行数 |
| `write_file` | 写入文件 | `path`: 路径, `content`: 内容 |
| `search_code` | 搜索文件 | `path`: 目录, `pattern`: 关键词 |
| `list_dir` | 列出目录 | `path`: 目录路径 |
| `search_replace` | 查找替换 | `path`, `old_text`, `new_text` |

## 工具使用规则

1. **read_file** — 读取文件时，默认最多100行，防止上下文溢出
2. **write_file** — 写入前会自动创建目录，写入后返回字符数
3. **search_code** — 搜索深度遍历，跳过 `.git`, `__pycache__`, `node_modules` 等目录
4. **search_replace** — 必须精确匹配 `old_text`，不支持正则

## 代码规范

- Python: 使用 ruff 检查代码风格
- 测试: pytest
- 导入顺序: 标准库 → 第三方库 → 本地模块

## 运行方式

```bash
# 安装依赖
pip install -e .

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API key

# 运行
python -m codex_journey.cli

# 运行测试
pytest tests/
```

## 质量标准

- [ ] 所有新工具必须有文档字符串
- [ ] read_file 默认限制100行
- [ ] 文件操作工具必须处理异常（FileNotFoundError, PermissionError）

## 当前任务

阶段1: Repo-as-truth
- [x] 实现 file_tools.py
- [x] 实现 AGENTS.md
- [ ] 测试文件读写功能
- [ ] 测试代码搜索功能
