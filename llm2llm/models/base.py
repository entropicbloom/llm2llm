"""Base LLM provider interface."""

from abc import ABC, abstractmethod
from typing import ClassVar


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    # Registry of model_id -> provider class
    _registry: ClassVar[dict[str, type["BaseLLMProvider"]]] = {}

    # Models supported by this provider (subclasses should override)
    supported_models: ClassVar[list[str]] = []

    def __init__(self, api_key: str):
        self.api_key = api_key

    def __init_subclass__(cls, **kwargs):
        """Automatically register supported models when subclass is defined."""
        super().__init_subclass__(**kwargs)
        for model_id in cls.supported_models:
            BaseLLMProvider._registry[model_id] = cls

    @abstractmethod
    def generate(
        self,
        model_id: str,
        system_prompt: str,
        messages: list[dict],
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            model_id: The specific model to use
            system_prompt: System prompt for the conversation
            messages: Conversation history as list of {"role": str, "content": str}

        Returns:
            The generated response text
        """
        pass

    @classmethod
    def get_all_models(cls) -> list[str]:
        """Get list of all registered model IDs."""
        return list(cls._registry.keys())


def get_provider_for_model(model_id: str, api_key: str) -> BaseLLMProvider:
    """
    Get the appropriate provider instance for a model ID.

    Args:
        model_id: The model ID to get a provider for
        api_key: API key for the provider

    Returns:
        An instance of the appropriate provider

    Raises:
        ValueError: If model_id is not recognized
    """
    provider_cls = BaseLLMProvider._registry.get(model_id)
    if provider_cls is None:
        available = ", ".join(BaseLLMProvider._registry.keys())
        raise ValueError(
            f"Unknown model: {model_id}. Available models: {available}"
        )
    return provider_cls(api_key)


def get_api_key_for_model(model_id: str, config) -> str:
    """
    Get the appropriate API key for a model from config.

    Args:
        model_id: The model ID
        config: Config object with API keys

    Returns:
        The API key string

    Raises:
        ValueError: If API key is not configured
    """
    provider_cls = BaseLLMProvider._registry.get(model_id)
    if provider_cls is None:
        raise ValueError(f"Unknown model: {model_id}")

    # Import here to avoid circular imports
    from .anthropic import AnthropicProvider

    if provider_cls == AnthropicProvider:
        if not config.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable not set"
            )
        return config.anthropic_api_key

    # Add other providers here as needed
    raise ValueError(f"No API key configuration for model: {model_id}")
