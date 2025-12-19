"""OpenRouter LLM provider implementation."""

import openai
from .base import BaseLLMProvider


class OpenRouterProvider(BaseLLMProvider):
    """Provider for OpenRouter models (OpenAI-compatible API)."""

    supported_models = [
        "google/gemini-3-flash-preview",
        "mistralai/ministral-3b",
        "mistralai/ministral-8b",
        "mistralai/ministral-8b-2410",
        "mistralai/ministral-3b-2410",
        "mistralai/ministral-14b-2512",
        "mistralai/mistral-large-2512",
        "openai/gpt-5.1",
        "openai/gpt-5-mini",
    ]

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

        response = self.client.chat.completions.create(
            model=model_id,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": system_prompt},
                *messages,
            ],
        )

        # Extract text content from response
        if not response.choices:
            raise ValueError(f"Empty response from model {model_id}")

        content = response.choices[0].message.content
        if content is None:
            raise ValueError(f"No content in response from model {model_id}")

        return content
