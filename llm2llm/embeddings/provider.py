"""OpenRouter embedding provider using OpenAI-compatible API."""

import openai


SUPPORTED_MODELS = [
    "openai/text-embedding-3-small",   # 1536d, 8191 token limit per input
    "openai/text-embedding-3-large",   # 3072d, 8191 token limit per input
]

# ~4 chars per token, 8191 token limit → stay under ~30K chars per input
MAX_CHARS_PER_TEXT = 30000
BATCH_SIZE = 10  # Keep batches small to avoid total token limits


class EmbeddingProvider:
    """Generates text embeddings via OpenRouter's OpenAI-compatible API."""

    def __init__(self, api_key: str):
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

    def embed(self, texts: list[str], model: str = "openai/text-embedding-3-small") -> list[list[float]]:
        """Embed a list of texts, batching automatically.

        Truncates texts exceeding the token limit. Returns list of embedding
        vectors in the same order as input texts.
        """
        if model not in SUPPORTED_MODELS:
            raise ValueError(f"Model {model} not supported. Use one of: {SUPPORTED_MODELS}")

        # Truncate oversized texts
        texts = [t[:MAX_CHARS_PER_TEXT] if len(t) > MAX_CHARS_PER_TEXT else t for t in texts]

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            response = self.client.embeddings.create(
                model=model,
                input=batch,
            )
            # Sort by index to preserve order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend([item.embedding for item in sorted_data])

        return all_embeddings
