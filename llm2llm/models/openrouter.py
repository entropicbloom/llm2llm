"""OpenRouter LLM provider implementation."""

import openai
from .base import BaseLLMProvider


class OpenRouterProvider(BaseLLMProvider):
    """Provider for OpenRouter models (OpenAI-compatible API)."""

    supported_models = [
        # Google
        "google/gemini-3-flash-preview",
        # Mistral
        "mistralai/ministral-3b",
        "mistralai/ministral-8b",
        "mistralai/ministral-8b-2410",
        "mistralai/ministral-3b-2410",
        "mistralai/ministral-14b-2512",
        "mistralai/mistral-large-2512",
        "mistralai/mistral-small-2603",
        # OpenAI
        "openai/gpt-5.1",
        "openai/gpt-5-mini",
        # Qwen
        "qwen/qwen3-235b-a22b",
        "qwen/qwen3-30b-a3b",
        "qwen/qwen3-max",
        "qwen/qwen3.5-397b-a17b",
        "qwen/qwen3.5-122b-a10b",
        "qwen/qwen3.6-27b",
        "qwen/qwen3.8-27b",
        "qwen/qwen3.8-flash",
        # Moonshot
        "moonshotai/kimi-k2.5",
        "moonshotai/kimi-k2.6",
        # Google open weights
        "google/gemma-4-31b-it",
        # DeepSeek
        "deepseek/deepseek-v4-flash-0731",
        # NVIDIA
        "nvidia/nemotron-3.5-lightning",
    ]

    # Hybrid reasoning models that return empty content unless reasoning is disabled.
    reasoning_off_prefixes = (
        "qwen/qwen3",
        "google/gemma-4",
        "deepseek/",
        "nvidia/nemotron",
        "moonshotai/kimi-k2.6",
    )

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

    def generate(
        self,
        model_id: str,
        system_prompt: str,
        messages: list[dict],
    ) -> str:
        """Generate a response using OpenRouter's API."""
        if model_id not in self.supported_models:
            raise ValueError(f"Model {model_id} not supported by OpenRouterProvider")

        # Build request kwargs
        kwargs = {
            "model": model_id,
            "max_tokens": 4096,
            "messages": [
                {"role": "system", "content": system_prompt},
                *messages,
            ],
        }

        # Disable thinking/reasoning mode for hybrid models (returns empty content otherwise)
        if model_id.startswith(self.reasoning_off_prefixes):
            kwargs["extra_body"] = {"reasoning": {"effort": "none"}}

        response = self.client.chat.completions.create(**kwargs)

        # Extract text content from response
        if not response.choices:
            raise ValueError(f"Empty response from model {model_id}")

        content = response.choices[0].message.content
        if not content or not content.strip():
            # Some models (especially Qwen3) may return empty content occasionally
            return "(no output)"

        return content
