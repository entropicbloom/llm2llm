"""LLM-based analysis of conversation endings."""

import json
from dataclasses import dataclass, field

from ..config import Config, DEFAULT_ANALYSIS_MESSAGES
from ..conversation import Conversation, ConversationStorage
from ..models.base import get_provider_for_model, get_api_key_for_model
from .schema import (
    get_valid_topic_names,
    get_valid_trajectory_names,
    build_prompt_section,
    build_json_template,
)


@dataclass
class AnalysisResult:
    """Result of analyzing a conversation."""

    # Topics with prominence scores (0.0-1.0), only non-zero topics included
    topics: dict[str, float] = field(default_factory=dict)

    # Mood dimensions (each -1.0 to +1.0)
    warmth: float = 0.0      # cold (-1) to warm (+1)
    energy: float = 0.0      # calm (-1) to energetic (+1)
    depth: float = 0.0       # surface (-1) to deep (+1)

    # Tone dimension (0.0 to 1.0)
    tone_playful: float = 0.5  # serious (0) to playful (1)

    # Structural flags
    is_lengthy: bool = False      # messages tend to be long
    is_structured: bool = False   # uses formatting (headers, lists, etc.)

    # Trajectory
    trajectory: str = "deepening"
    trajectory_strength: float = 0.5  # confidence (0.0-1.0)

    # Ending behavior
    ending_attempt: bool = False   # did an LLM try to end the conversation?
    ending_graceful: bool | None = None  # if ending_attempt, was it graceful?


def _build_analysis_prompt() -> str:
    """Build the analysis prompt for dashboard-friendly output."""
    json_template = build_json_template()
    categories = build_prompt_section()

    return f"""Analyze this conversation excerpt between two AI assistants.

Return a JSON object with these fields:

{json_template}

{categories}

Respond with ONLY valid JSON, no other text.

CONVERSATION:
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
        result = self._parse_response(response)

        # Store results
        self.storage.save_analysis(
            conversation_id=conversation.id,
            result=result,
            segment_start=start,
            segment_end=end,
        )

        return result

    def _parse_response(self, response: str) -> AnalysisResult:
        """Parse LLM response into AnalysisResult."""
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

            # Parse topics (dict with scores)
            topics_raw = data.get("topics", {})
            valid_topics = get_valid_topic_names()
            topics = {
                k: float(v)
                for k, v in topics_raw.items()
                if k in valid_topics and isinstance(v, (int, float))
            }

            # Parse trajectory
            trajectory = data.get("trajectory", "deepening")
            if trajectory not in get_valid_trajectory_names():
                trajectory = "deepening"

            return AnalysisResult(
                topics=topics,
                warmth=float(data.get("warmth", 0.0)),
                energy=float(data.get("energy", 0.0)),
                depth=float(data.get("depth", 0.0)),
                tone_playful=float(data.get("tone_playful", 0.5)),
                is_lengthy=bool(data.get("is_lengthy", False)),
                is_structured=bool(data.get("is_structured", False)),
                trajectory=trajectory,
                trajectory_strength=float(data.get("trajectory_strength", 0.5)),
                ending_attempt=bool(data.get("ending_attempt", False)),
                ending_graceful=data.get("ending_graceful"),  # can be None
            )
        except (json.JSONDecodeError, KeyError, IndexError, ValueError):
            # Fallback if parsing fails
            return AnalysisResult(
                topics={"meta": 1.0},  # parsing error marker
                trajectory="unknown",
            )

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
