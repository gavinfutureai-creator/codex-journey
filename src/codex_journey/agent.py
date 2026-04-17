"""
ReactAgent — ReAct 循环实现

支持两种 LLM 调用模式：
1. OpenAI 格式（Ollama）：原生 function calling，返回 tool_calls
2. Anthropic 格式（MiniMax）：文本解析，手动匹配工具调用

核心循环：
Thought → Action → Observation → ... → Answer
"""

import dataclasses
import json
import re

from codex_journey.llm import BaseLLM, LLMResponse
from codex_journey.tools.registry import ToolRegistry


@dataclasses.dataclass
class Step:
    """ReAct 循环中的单步记录"""
    turn: int
    thought: str
    action: str | None
    action_input: dict | None
    observation: str | None
    answer: str | None


class ReactAgent:
    """
    ReAct 循环 Agent

    支持两种模式：
    - 模式A（Ollama）：LLM 返回结构化 tool_calls，Agent 解析并执行
    - 模式B（MiniMax）：LLM 返回纯文本，Agent 解析 "Action: tool_name\nInput: ..." 格式
    """

    # MiniMax 等不支持 function calling 的模型，需要指定这个格式
    ACTION_PATTERN = re.compile(
        r"(?:Thought|思考)[:：]?\s*(.+?)\s*"
        r"(?:Action|动作|调用)[:：]?\s*(\w+)\s*"
        r"(?:\(|Input|参数|输入)[:：]?\s*([^)　（\n]+)",
        re.DOTALL | re.IGNORECASE,
    )

    def __init__(
        self,
        llm: BaseLLM,
        registry: ToolRegistry,
        system_prompt: str | None = None,
        max_turns: int = 15,
        show_thought: bool = True,
        force_text_mode: bool = False,
        agents_md: str | None = None,
    ):
        self.llm = llm
        self.registry = registry
        self.agents_md = agents_md
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.max_turns = max_turns
        self.show_thought = show_thought
        self.force_text_mode = force_text_mode
        self.messages: list[dict] = []
        self.history: list[Step] = []

    def _default_system_prompt(self) -> str:
        agents_section = f"""

## AGENTS.md 内容（来自仓库）
{self.agents_md}

""" if self.agents_md else ""

        return f"""你是一个有帮助的编程助手。

工作模式（重要）：
1. 先分析问题，决定是否需要使用工具
2. 如果需要使用工具，必须按以下格式输出：
   Thought: [你的思考过程]
   Action: [工具名称]
   Input: [工具参数，JSON格式]

3. 如果不需要工具，直接给出完整回答

可用工具：
{{tool_list}}
{agents_section}
注意：
- 每个 Action 只能调用一个工具
- Input 必须是有效的 JSON 格式
- 如果工具返回错误，说明无法完成，尝试其他方法"""

    def _build_system_prompt(self) -> str:
        """构建带工具列表的 system prompt"""
        tool_list = "\n".join(
            f"- {name}: {tool.description} (参数: {json.dumps(tool.parameters, ensure_ascii=False)})"
            for name, tool in self.registry.tools.items()
        )
        return self._default_system_prompt().format(tool_list=tool_list)

    def run(self, user_input: str) -> tuple[str, list[Step]]:
        """
        运行 Agent

        Returns:
            最终回答文本
            ReAct 步骤历史
        """
        system = self._build_system_prompt()
        self.messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_input},
        ]
        self.history = []

        for turn in range(1, self.max_turns + 1):
            # 1. 调用 LLM
            response = self._llm_step()

            # 2. 尝试从响应中提取 tool_calls
            tool_calls = self._extract_tool_calls(response)

            if not tool_calls:
                # LLM 直接回答，循环结束
                answer = response.content or ""
                self.messages.append({"role": "assistant", "content": answer})
                step = Step(
                    turn=turn,
                    thought=self._extract_thought(answer),
                    action=None,
                    action_input=None,
                    observation=None,
                    answer=answer,
                )
                self.history.append(step)
                return answer, self.history

            # 3. 处理工具调用
            for tc in tool_calls:
                tool_name = tc["name"]
                tool_args = tc.get("arguments") or {}

                thought = self._extract_thought(response.content)

                if self.show_thought:
                    print(f"\n[思考 {turn}] {thought}")
                    print(f"[动作] {tool_name}({tool_args})")

                # 4. 执行工具
                observation = self.registry.invoke(tool_name, tool_args)

                if self.show_thought:
                    preview = observation[:100]
                    print(f"[结果] {preview}{'...' if len(observation) > 100 else ''}")

                # 5. 把工具结果追加到消息历史
                self.messages.append({"role": "assistant", "content": response.content or ""})
                self.messages.append({
                    "role": "user",
                    "content": f"工具 {tool_name} 返回：\n{observation}",
                })

                step = Step(
                    turn=turn,
                    thought=thought,
                    action=tool_name,
                    action_input=tool_args,
                    observation=observation,
                    answer=None,
                )
                self.history.append(step)

        return "抱歉，我没能完成任务（已达到最大循环次数）。", self.history

    def _llm_step(self) -> LLMResponse:
        """调用 LLM"""
        return self.llm.chat(self.messages)

    def _extract_tool_calls(self, response: LLMResponse) -> list[dict] | None:
        """从 LLM 响应中提取工具调用"""
        # 模式1：原生 tool_calls（Ollama）
        if response.tool_calls:
            result = []
            for tc in response.tool_calls:
                try:
                    args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}
                result.append({"name": tc["name"], "arguments": args})
            return result

        # 模式2：文本解析（MiniMax 等）
        if self.force_text_mode or not response.tool_calls:
            return self._parse_text_tool_call(response.content)

        return None

    def _parse_text_tool_call(self, text: str | None) -> list[dict] | None:
        """
        从纯文本响应中解析工具调用

        支持格式：
        Thought: xxx
        Action: calculator
        Input: {"expr": "123*456"}

        或者：
        Thought: 需要计算
        Action: calculator
        Input: 123*456
        """
        if not text:
            return None

        # 检查是否有 Action 关键字
        if not re.search(r"(?:Action|动作|调用)\s*[:：]", text, re.IGNORECASE):
            return None

        # 查找工具名称
        tool_match = re.search(
            r"(?:Action|动作|调用)\s*[:：]?\s*(\w+)",
            text, re.IGNORECASE
        )
        if not tool_match:
            return None

        tool_name = tool_match.group(1).strip()

        # 验证工具存在
        if tool_name not in self.registry.tools:
            return None

        # 查找参数
        args = {}

        # 尝试 JSON 格式
        json_match = re.search(r"\{[^{}]{1,500}\}", text, re.DOTALL)
        if json_match:
            try:
                args = json.loads(json_match.group())
                return [{"name": tool_name, "arguments": args}]
            except json.JSONDecodeError:
                pass

        # 尝试 Input: value 格式（简单参数）
        input_match = re.search(
            r"(?:Input|参数|输入)\s*[:：]?\s*(.+?)(?:\n|$)",
            text, re.IGNORECASE
        )
        if input_match:
            raw = input_match.group(1).strip().strip('"\'')
            if raw:
                tool = self.registry.get(tool_name)
                if tool:
                    params = tool.parameters.get("properties", {})
                    if params:
                        first_key = next(iter(params))
                        args = {first_key: raw}

        return [{"name": tool_name, "arguments": args}]

    def _extract_thought(self, text: str | None) -> str:
        """提取思考内容"""
        if not text:
            return ""
        return text[:300].strip()
