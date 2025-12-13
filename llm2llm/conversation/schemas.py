"""Data schemas for conversations."""

from datetime import datetime
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field
import uuid


class ConversationStatus(str, Enum):
    """Status of a conversation."""

    ACTIVE = "active"  # Conversation in progress
    COMPLETED = "completed"  # Reached max turns
    PAUSED = "paused"  # Manually paused, can be continued
    ANALYZED = "analyzed"  # Has been analyzed


class ParticipantRole(str, Enum):
    """Role of a participant in the conversation."""

    INITIATOR = "initiator"  # LLM1 - starts the conversation
    RESPONDER = "responder"  # LLM2 - responds to initiator


class Message(BaseModel):
    """A single message in the conversation."""

    role: Literal["assistant"]  # Both LLMs appear as assistants
    content: str
    model_id: str  # Which model generated this message
    participant_role: ParticipantRole  # initiator or responder
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    turn_number: int  # 1-indexed turn number


class Conversation(BaseModel):
    """A conversation between two LLMs."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    llm1_model: str  # Model ID for initiator
    llm2_model: str  # Model ID for responder
    messages: list[Message] = Field(default_factory=list)
    status: ConversationStatus = ConversationStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def turn_count(self) -> int:
        """Number of turns (messages) in the conversation."""
        return len(self.messages)

    @property
    def ordered_pair(self) -> tuple[str, str]:
        """Return the ordered pair of models (llm1, llm2)."""
        return (self.llm1_model, self.llm2_model)

    def add_message(
        self,
        content: str,
        model_id: str,
        participant_role: ParticipantRole,
    ) -> Message:
        """Add a message to the conversation."""
        message = Message(
            role="assistant",
            content=content,
            model_id=model_id,
            participant_role=participant_role,
            turn_number=len(self.messages) + 1,
        )
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        return message

    def get_history_for_participant(
        self, participant_role: ParticipantRole
    ) -> list[dict]:
        """
        Get conversation history formatted for a participant.

        The initiator sees:
        - Their own messages as "assistant"
        - Responder's messages as "user"

        The responder sees:
        - Initiator's messages as "user"
        - Their own messages as "assistant"
        """
        history = []
        for msg in self.messages:
            if msg.participant_role == participant_role:
                history.append({"role": "assistant", "content": msg.content})
            else:
                history.append({"role": "user", "content": msg.content})
        return history
