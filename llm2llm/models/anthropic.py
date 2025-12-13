"""Anthropic LLM provider implementation."""

import anthropic
from .base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    """Provider for Anthropic Claude models."""

    supported_models = [
        # Claude 4.5 models (latest)
        "claude-opus-4-5-20251101",
        "claude-sonnet-4-5-20250929",
        "claude-haiku-4-5-20251001",
        # Claude 4.1 models
        "claude-opus-4-1-20250805",
        # Claude 4 models
        "claude-opus-4-20250514",
        "claude-sonnet-4-20250514",
        # Claude 3.7 models
        "claude-3-7-sonnet-20250219",
        # Claude 3.5 models
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        # Claude 3 models
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate(
        self,
        model_id: str,
        system_prompt: str,
        messages: list[dict],
    ) -> str:
        """Generate a response using Anthropic's API."""
        if model_id not in self.supported_models:
            raise ValueError(f"Model {model_id} not supported by AnthropicProvider")

        response = self.client.messages.create(
            model=model_id,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        )

        # Extract text content from response
        if not response.content:
            raise ValueError(f"Empty response from model {model_id}")
        content = response.content[0]
        if hasattr(content, "text"):
            return content.text
        return str(content)
