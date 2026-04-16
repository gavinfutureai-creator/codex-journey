"""
CodexJourney CLI

命令行入口。
"""

import sys

from rich.console import Console
from rich.markdown import Markdown

from codex_journey import __version__
from codex_journey.agent import ReactAgent
from codex_journey.llm import create_llm
from codex_journey.tools.registry import build_default_registry

console = Console()


def main():
    console.print(f"[bold blue]CodexJourney v{__version__}[/bold blue]")
    console.print("[dim]基于 Harness 理论的自主编码 Agent[/dim]\n")

    # 1. 创建 LLM
    llm = create_llm(provider="minimax")

    # 2. 创建工具注册表
    registry = build_default_registry()

    # 3. 创建 Agent
    agent = ReactAgent(llm=llm, registry=registry, show_thought=True)

    console.print("[dim]可用工具:[/dim]", ", ".join(registry.list_tools()))
    console.print("[dim]输入问题开始对话，输入 'quit' 退出[/dim]\n")
    console.print("─" * 50)

    # 交互式循环
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

        # 运行 Agent
        try:
            answer, steps = agent.run(user_input)

            console.print("\n" + "─" * 50)
            console.print("[bold]最终回答:[/bold]")
            console.print(Markdown(answer))

        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")


if __name__ == "__main__":
    main()
