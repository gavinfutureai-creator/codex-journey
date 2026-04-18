"""
CodexJourney CLI

命令行入口。
支持两种模式：
- single：单 Agent 模式（默认）
- multi：多 Agent 协作模式（Coordinator + Worker）
"""

import argparse
import os

from dotenv import load_dotenv

load_dotenv()

from rich.console import Console
from rich.markdown import Markdown

from codex_journey import __version__
from codex_journey.agent import ReactAgent
from codex_journey.llm import create_llm
from codex_journey.tools.registry import build_default_registry

console = Console()


def load_agents_md() -> str:
    """启动时自动读取 AGENTS.md"""
    try:
        # 查找项目根目录（向上查找 AGENTS.md）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        agents_md_path = os.path.join(project_root, "AGENTS.md")

        if os.path.exists(agents_md_path):
            with open(agents_md_path, "r", encoding="utf-8") as f:
                content = f.read()
            console.print(f"[dim]已加载 AGENTS.md[/dim]")
            return content
        else:
            console.print(f"[yellow]警告: 未找到 AGENTS.md[/yellow]")
            return ""
    except Exception as e:
        console.print(f"[yellow]警告: 读取 AGENTS.md 失败: {e}[/yellow]")
        return ""


def run_single_mode(task: str, llm, registry, agents_content: str) -> None:
    """单 Agent 模式"""
    agent = ReactAgent(
        llm=llm,
        registry=registry,
        show_thought=True,
        agents_md=agents_content,
    )

    console.print(f"[dim]模式: 单 Agent[/dim]\n")
    console.print("[bold green]>[/bold green] " + task)

    answer, steps = agent.run(task)

    console.print("\n" + "─" * 50)
    console.print("[bold]最终回答:[/bold]")
    console.print(Markdown(answer))


def run_multi_mode(task: str, llm_provider: str, registry, agents_content: str) -> None:
    """多 Agent 协作模式"""
    from codex_journey.harness import CoordinatorAgent, WorkerAgent

    coordinator = CoordinatorAgent(
        llm_provider=llm_provider,
        registry=registry,
        show_thought=True,
    )
    worker = WorkerAgent(
        llm_provider=llm_provider,
        registry=registry,
        show_thought=True,
    )

    console.print(f"[dim]模式: 多 Agent 协作[/dim]\n")
    console.print("[bold green]>[/bold green] " + task)

    plan = coordinator.coordinate(task, worker)

    console.print("\n" + "─" * 50)
    console.print("[bold]任务执行完成[/bold]")
    console.print(plan.summary())


def main():
    parser = argparse.ArgumentParser(
        description="CodexJourney — 基于 Harness 理论的自主编码 Agent",
    )
    parser.add_argument(
        "task",
        nargs="?",
        default=None,
        help="要执行的任务描述（不指定则进入交互模式）",
    )
    parser.add_argument(
        "--mode",
        choices=["single", "multi"],
        default="single",
        help="运行模式：single=单 Agent，multi=多 Agent 协作（默认 single）",
    )

    args = parser.parse_args()

    console.print(f"[bold blue]CodexJourney v{__version__}[/bold blue]")
    console.print("[dim]基于 Harness 理论的自主编码 Agent[/dim]\n")

    # 加载 AGENTS.md
    agents_content = load_agents_md()

    # 初始化 LLM 和 registry
    llm = create_llm(provider="minimax")
    registry = build_default_registry()

    console.print("[dim]可用工具:[/dim]", ", ".join(registry.list_tools()))
    console.print("")

    if args.task:
        # 命令行参数模式：执行任务后退出
        if args.mode == "multi":
            run_multi_mode(args.task, "minimax", registry, agents_content)
        else:
            run_single_mode(args.task, llm, registry, agents_content)
        return

    # 交互式循环（仅 single 模式支持）
    if args.mode == "multi":
        console.print("[yellow]多 Agent 模式需要指定任务，使用:[/yellow]")
        console.print("  python -m codex_journey.cli <任务描述> --mode multi")
        return

    console.print("[dim]输入问题开始对话，输入 'quit' 退出[/dim]\n")
    console.print("─" * 50)

    agent = ReactAgent(
        llm=llm,
        registry=registry,
        show_thought=True,
        agents_md=agents_content,
    )

    while True:
        try:
            user_input = console.input("\n[bold green]>[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]退出[/yellow]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[yellow]再见[/yellow]")
            break

        try:
            answer, steps = agent.run(user_input)

            console.print("\n" + "─" * 50)
            console.print("[bold]最终回答:[/bold]")
            console.print(Markdown(answer))

        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")


if __name__ == "__main__":
    main()
