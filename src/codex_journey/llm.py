"""
LLM 调用层

支持 MiniMax（Anthropic 格式）和 Ollama（OpenAI 兼容格式）
MiniMax 使用 Anthropic API，不支持 function calling，
所以工具调用通过 ReAct 文本解析实现。
"""

import json
import os
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    tool_calls: list[dict] | None = None


class BaseLLM:
    """LLM 基类"""

    def chat(self, messages: list[dict], functions: list[dict] | None = None) -> LLMResponse:
        raise NotImplementedError


class MiniMaxLLM(BaseLLM):
    """
    MiniMax API（Anthropic 兼容格式）

    注意：MiniMax 不支持 function calling 协议，
    工具调用通过 ReAct 文本解析实现。
    """

    def __init__(
        self,
        model: str = "MiniMax-M2.7",
        api_key: str | None = None,
        base_url: str = "https://api.minimaxi.com/anthropic",
        timeout: int = 120,
        max_tokens: int = 8192,
    ):
        import httpx

        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_tokens = max_tokens
        self._client = httpx.Client(
            timeout=timeout,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )

    def chat(self, messages: list[dict], functions: list[dict] | None = None) -> LLMResponse:
        """
        调用 MiniMax API

        如果 messages 中有 tool_results（来自工具调用的结果），
        则追加到请求中，让 LLM 继续处理。
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
        }

        # 如果有 functions schema，追加到 system prompt 中
        # （MiniMax 不原生支持 function calling，这里做兼容处理）
        if functions:
            tool_descriptions = "\n\n".join(
                f"工具 {i+1}: {f['function']['name']}\n"
                f"描述: {f['function']['description']}\n"
                f"参数: {json.dumps(f['function']['parameters'], ensure_ascii=False)}"
                for i, f in enumerate(functions)
            )
            # 把工具说明注入到 system prompt 或 user message
            pass  # MiniMax 不支持，这里由 ReActLoop 通过文本解析处理

        response = self._client.post(
            f"{self.base_url}/v1/messages",
            json=payload,
        )

        if response.status_code != 200:
            raise RuntimeError(f"MiniMax API 错误 ({response.status_code}): {response.text}")

        data = response.json()

        # 提取文本内容（跳过 thinking 块）
        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content = block["text"]
                break

        return LLMResponse(content=content)


class OllamaLLM(BaseLLM):
    """Ollama 本地模型（OpenAI 兼容格式）"""

    def __init__(
        self,
        model: str = "qwen3.5:9b",
        base_url: str = "http://localhost:11434/v1",
    ):
        import openai

        self.model = model
        self.client = openai.OpenAI(base_url=base_url, api_key="ollama")

    def chat(self, messages: list[dict], functions: list[dict] | None = None) -> LLMResponse:
        kwargs: dict = {
            "model": self.model,
            "messages": messages,
        }

        if functions:
            kwargs["tools"] = functions
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
                for tc in choice.message.tool_calls
            ]
            return LLMResponse(content="", tool_calls=tool_calls)

        return LLMResponse(content=choice.message.content or "")


def create_llm(provider: str = "minimax", **kwargs) -> BaseLLM:
    """工厂函数：创建 LLM 实例"""
    if provider == "minimax":
        return MiniMaxLLM(**kwargs)
    elif provider == "ollama":
        return OllamaLLM(**kwargs)
    else:
        raise ValueError(f"不支持的 provider: {provider}")
