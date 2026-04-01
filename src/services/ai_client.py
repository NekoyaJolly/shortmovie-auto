"""Claude API ラッパー"""

from __future__ import annotations

import json
import logging

import anthropic

from src.config import get_env, get_settings

logger = logging.getLogger(__name__)


class AIClient:
    def __init__(self) -> None:
        settings = get_settings()
        api_key = get_env("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY が設定されていません")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = settings.ai.model
        self.max_tokens = settings.ai.max_tokens

    def generate(self, prompt: str, system: str = "", max_tokens: int | None = None) -> str:
        """テキスト生成"""
        messages = [{"role": "user", "content": prompt}]
        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def generate_json(self, prompt: str, system: str = "") -> dict | list:
        """JSONレスポンスを返すプロンプト実行"""
        system_with_json = (
            system + "\n\n" if system else ""
        ) + "必ずJSON形式のみで回答してください。マークダウンのコードブロックは使わないでください。"

        text = self.generate(prompt, system=system_with_json)

        # コードブロックで囲まれていた場合の対応
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]  # ```json を除去
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        return json.loads(text)
