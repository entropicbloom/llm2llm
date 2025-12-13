"""LLM-based analysis of conversation endings."""

import json
from dataclasses import dataclass

from ..config import Config, DEFAULT_ANALYSIS_MESSAGES
from ..conversation import Conversation, ConversationStorage
from ..models.base import get_provider_for_model, get_api_key_for_model


@dataclass
class AnalysisResult:
    """Result of analyzing a conversation."""

    topics: list[str]  # Main topics/themes discussed
    mood: str  # Emotional tone (curious, playful, philosophical, etc.)
    trajectory: str  # Conversation trajectory (converging, diverging, deepening)


ANALYSIS_PROMPT = """Analyze the following conversation excerpt (the last few messages from a longer conversation between two AI assistants).

Provide your analysis in the following JSON format:
{
    "topics": ["topic1", "topic2", "topic3"],
    "mood": "one word or short phrase describing the emotional tone",
    "trajectory": "one of: converging (coming to agreement/conclusion), diverging (exploring new directions), deepening (going deeper into a topic), cycling (returning to earlier themes), concluding (wrapping up)"
}

Focus on:
1. Topics: What themes or subjects are being discussed? List 2-5 key topics.
2. Mood: What's the emotional tone? (e.g., curious, playful, philosophical, serious, collaborative, debating, reflective, enthusiastic)
3. Trajectory: How is the conversation evolving?

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
        self.analysis_model = analysis_model or "claude-3-5-haiku-20241022"
        self.messages_to_analyze = messages_to_analyze

    def analyze(self, conversation: Conversation) -> AnalysisResult:
        """
        Analyze a conversation and store the results.

        Args:
            conversation: The conversation to analyze

        Returns:
            AnalysisResult with topics, mood, and trajectory
        """
        # Get the last N messages
        messages = conversation.messages[-self.messages_to_analyze:]

        # Format messages for the prompt
        excerpt = "\n\n".join(
            f"[{msg.participant_role.value.upper()}]: {msg.content}"
            for msg in messages
        )

        # Get provider for analysis
        api_key = get_api_key_for_model(self.analysis_model, self.config)
        provider = get_provider_for_model(self.analysis_model, api_key)

        # Run analysis
        response = provider.generate(
            model_id=self.analysis_model,
            system_prompt="You are an expert conversation analyst. Respond only with valid JSON.",
            messages=[{"role": "user", "content": ANALYSIS_PROMPT + excerpt}],
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

            result = AnalysisResult(
                topics=data.get("topics", []),
                mood=data.get("mood", "unknown"),
                trajectory=data.get("trajectory", "unknown"),
            )
        except (json.JSONDecodeError, KeyError, IndexError):
            # Fallback if parsing fails
            result = AnalysisResult(
                topics=["parsing_error"],
                mood="unknown",
                trajectory="unknown",
            )

        # Store results
        self.storage.save_analysis(
            conversation_id=conversation.id,
            topics=result.topics,
            mood=result.mood,
            trajectory=result.trajectory,
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
