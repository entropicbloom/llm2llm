"""LLM-based analysis of conversation endings."""

import json
from dataclasses import dataclass
from pathlib import Path

from ..config import Config, DEFAULT_ANALYSIS_MESSAGES
from ..conversation import Conversation, ConversationStorage
from ..models.base import get_provider_for_model, get_api_key_for_model


@dataclass
class AnalysisResult:
    """Result of analyzing a conversation."""

    topics: list[str]  # Main topics/themes discussed
    mood: list[str]  # Emotional tone(s) - 1 or 2 values
    trajectory: str  # Conversation trajectory (converging, diverging, deepening)


def _load_categories() -> str:
    """Load the categories markdown file."""
    categories_path = Path(__file__).parent / "categories.md"
    return categories_path.read_text()


def _build_analysis_prompt() -> str:
    """Build the analysis prompt with categories from the shared file."""
    categories = _load_categories()
    return f"""Analyze the following conversation excerpt (the last few messages from a longer conversation between two AI assistants).

Provide your analysis in the following JSON format:
{{
    "topics": ["topic1", "topic2", "topic3"],
    "mood": ["mood1"] or ["mood1", "mood2"],
    "trajectory": "trajectory_value"
}}

{categories}

Respond ONLY with valid JSON, no other text.

CONVERSATION EXCERPT:
"""


class ConversationAnalyzer:
    """Analyzes conversations using an LLM."""

    def __init__(
        self,
        config: Config,
        storage: ConversationStorage,
        analysis_model: str | None = None,
        messages_to_analyze: int = DEFAULT_ANALYSIS_MESSAGES,
    ):
        self.config = config
        self.storage = storage
        self.analysis_model = analysis_model or "claude-sonnet-4-5-20250929"
        self.messages_to_analyze = messages_to_analyze

    def analyze(
        self,
        conversation: Conversation,
        start: int = -5,
        end: int | None = None,
    ) -> AnalysisResult:
        """
        Analyze a conversation segment and store the results.

        Args:
            conversation: The conversation to analyze
            start: Start index for message segment (default: -5, last 5 messages)
            end: End index for message segment (default: None, to the end)

        Returns:
            AnalysisResult with topics, mood, and trajectory
        """
        # Slice messages based on start/end indices
        if end is None:
            messages = conversation.messages[start:]
        else:
            messages = conversation.messages[start:end]

        # Format messages for the prompt
        excerpt = "\n\n".join(
            f"[{msg.participant_role.value.upper()}]: {msg.content}"
            for msg in messages
        )

        # Get provider for analysis
        api_key = get_api_key_for_model(self.analysis_model, self.config)
        provider = get_provider_for_model(self.analysis_model, api_key)

        # Run analysis
        analysis_prompt = _build_analysis_prompt()
        response = provider.generate(
            model_id=self.analysis_model,
            system_prompt="You are an expert conversation analyst. Respond only with valid JSON.",
            messages=[{"role": "user", "content": analysis_prompt + excerpt}],
        )

        # Parse response
        try:
            # Try to extract JSON from response
            response_text = response.strip()
            # Handle case where response might have markdown code blocks
            if "```json" in response_text:
                parts = response_text.split("```json")
                if len(parts) > 1:
                    inner_parts = parts[1].split("```")
                    if inner_parts:
                        response_text = inner_parts[0]
            elif "```" in response_text:
                parts = response_text.split("```")
                if len(parts) > 1:
                    response_text = parts[1]

            data = json.loads(response_text)

            # Handle mood as list (new format) or string (old format)
            mood_data = data.get("mood", ["unknown"])
            if isinstance(mood_data, str):
                mood_data = [mood_data]

            result = AnalysisResult(
                topics=data.get("topics", []),
                mood=mood_data,
                trajectory=data.get("trajectory", "unknown"),
            )
        except (json.JSONDecodeError, KeyError, IndexError):
            # Fallback if parsing fails
            result = AnalysisResult(
                topics=["parsing_error"],
                mood=["unknown"],
                trajectory="unknown",
            )

        # Store results
        self.storage.save_analysis(
            conversation_id=conversation.id,
            topics=result.topics,
            mood=result.mood,
            trajectory=result.trajectory,
            segment_start=start,
            segment_end=end,
        )

        return result

    def analyze_batch(
        self,
        llm1_model: str | None = None,
        llm2_model: str | None = None,
    ) -> list[tuple[str, AnalysisResult]]:
        """
        Analyze all conversations that need analysis.

        Args:
            llm1_model: Optional filter by initiator model
            llm2_model: Optional filter by responder model

        Returns:
            List of (conversation_id, result) tuples
        """
        results = []

        for conversation in self.storage.get_conversations_for_analysis(
            llm1_model, llm2_model
        ):
            result = self.analyze(conversation)
            results.append((conversation.id, result))

        return results
