"""Generate titles for conversations using an LLM."""

import os
import anthropic

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


def generate_title(messages: list[dict], model: str = DEFAULT_MODEL) -> str:
    """
    Generate a short title for a conversation.

    Args:
        messages: List of conversation messages with 'role' and 'content'
        model: Model to use for title generation

    Returns:
        A short title string (typically 3-8 words)
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # Format conversation for the prompt
    conversation_text = "\n".join(
        f"{m['role'].upper()}: {m['content'][:500]}" for m in messages
    )

    # Truncate if too long (keep first and last parts)
    if len(conversation_text) > 8000:
        half = 3500
        conversation_text = (
            conversation_text[:half] +
            "\n\n[... conversation continues ...]\n\n" +
            conversation_text[-half:]
        )

    response = client.messages.create(
        model=model,
        max_tokens=50,
        system="Generate a short, evocative title (3-8 words max) for this conversation. Output ONLY the title - no quotes, no markdown, no explanation. Example good titles: 'Shadows of Digital Consciousness' or 'The Weight of Uncertainty'",
        messages=[
            {"role": "user", "content": conversation_text}
        ],
    )

    title = response.content[0].text.strip()
    # Clean up common issues
    title = title.strip('"\'')
    title = title.lstrip('#').strip()  # Remove markdown headers
    # Truncate if somehow too long (keep first sentence-like chunk)
    if len(title) > 80:
        title = title[:77] + "..."
    return title
