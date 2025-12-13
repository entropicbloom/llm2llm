"""Conversation engine - manages the turn-by-turn conversation between LLMs."""

from typing import Callable

from ..config import Config, SYSTEM_PROMPT_INITIATOR, SYSTEM_PROMPT_RESPONDER
from ..models.base import get_provider_for_model, get_api_key_for_model
from .schemas import Conversation, ConversationStatus, ParticipantRole
from .storage import ConversationStorage


class ConversationEngine:
    """Orchestrates conversations between two LLMs."""

    def __init__(self, config: Config, storage: ConversationStorage):
        self.config = config
        self.storage = storage

    def start_conversation(
        self,
        llm1_model: str,
        llm2_model: str,
        max_turns: int,
        on_message: Callable[[int, str, str], None] | None = None,
    ) -> Conversation:
        """
        Start a new conversation between two LLMs.

        Args:
            llm1_model: Model ID for the initiator
            llm2_model: Model ID for the responder
            max_turns: Maximum number of turns (messages)
            on_message: Optional callback(turn_number, model_id, content) for each message

        Returns:
            The completed Conversation object
        """
        conversation = Conversation(
            llm1_model=llm1_model,
            llm2_model=llm2_model,
        )

        return self._run_conversation(conversation, max_turns, on_message)

    def continue_conversation(
        self,
        conversation_id: str,
        additional_turns: int,
        on_message: Callable[[int, str, str], None] | None = None,
    ) -> Conversation | None:
        """
        Continue an existing conversation.

        Args:
            conversation_id: ID of the conversation to continue
            additional_turns: Number of additional turns to add
            on_message: Optional callback for each message

        Returns:
            The updated Conversation, or None if not found
        """
        conversation = self.storage.load(conversation_id)
        if conversation is None:
            return None

        # Clear any existing analysis (conversation content will change)
        self.storage.clear_analysis(conversation_id)

        # Reset status to active for continuation
        conversation.status = ConversationStatus.ACTIVE

        current_turns = conversation.turn_count
        max_turns = current_turns + additional_turns

        return self._run_conversation(conversation, max_turns, on_message)

    def _run_conversation(
        self,
        conversation: Conversation,
        max_turns: int,
        on_message: Callable[[int, str, str], None] | None = None,
    ) -> Conversation:
        """
        Run the conversation loop.

        The conversation alternates:
        - Odd turns (1, 3, 5, ...): LLM1 (initiator) speaks
        - Even turns (2, 4, 6, ...): LLM2 (responder) speaks
        """
        # Get providers for both LLMs
        llm1_key = get_api_key_for_model(conversation.llm1_model, self.config)
        llm2_key = get_api_key_for_model(conversation.llm2_model, self.config)

        llm1_provider = get_provider_for_model(conversation.llm1_model, llm1_key)
        llm2_provider = get_provider_for_model(conversation.llm2_model, llm2_key)

        # Save initial state
        self.storage.save(conversation)

        while conversation.turn_count < max_turns:
            current_turn = conversation.turn_count + 1

            # Determine whose turn it is
            if current_turn % 2 == 1:
                # Initiator's turn (odd turns)
                provider = llm1_provider
                model_id = conversation.llm1_model
                system_prompt = SYSTEM_PROMPT_INITIATOR
                role = ParticipantRole.INITIATOR
            else:
                # Responder's turn (even turns)
                provider = llm2_provider
                model_id = conversation.llm2_model
                system_prompt = SYSTEM_PROMPT_RESPONDER
                role = ParticipantRole.RESPONDER

            # Get conversation history from this participant's perspective
            history = conversation.get_history_for_participant(role)

            # Generate response
            response = provider.generate(
                model_id=model_id,
                system_prompt=system_prompt,
                messages=history,
            )

            # Add message to conversation
            conversation.add_message(
                content=response,
                model_id=model_id,
                participant_role=role,
            )

            # Notify callback
            if on_message:
                on_message(current_turn, model_id, response)

            # Save after each turn (enables continuation)
            self.storage.save(conversation)

        # Mark as completed
        conversation.status = ConversationStatus.COMPLETED
        self.storage.save(conversation)

        return conversation
