"""JSON sidecar storage for conversation embeddings."""

import json
from pathlib import Path


class EmbeddingStorage:
    """Manages embedding sidecar files alongside conversation JSON files.

    Sidecar files are stored at: conversations/{uuid}.embeddings.json
    Format:
    {
        "model": "openai/text-embedding-3-small",
        "messages": [
            {
                "turn_number": 1,
                "participant_role": "initiator",
                "embedding": [0.1, 0.2, ...]
            },
            ...
        ]
    }
    """

    def __init__(self, conversations_dir: Path):
        self.conversations_dir = conversations_dir

    def _sidecar_path(self, conversation_id: str) -> Path:
        return self.conversations_dir / f"{conversation_id}.embeddings.json"

    def has_embeddings(self, conversation_id: str) -> bool:
        """Check if embeddings exist for a conversation."""
        return self._sidecar_path(conversation_id).exists()

    def save_embeddings(
        self,
        conversation_id: str,
        model: str,
        messages: list[dict],
    ) -> None:
        """Save embeddings sidecar file.

        messages: list of dicts with turn_number, participant_role, embedding keys.
        """
        data = {
            "model": model,
            "messages": messages,
        }
        path = self._sidecar_path(conversation_id)
        with open(path, "w") as f:
            json.dump(data, f)

    def load_embeddings(self, conversation_id: str) -> dict | None:
        """Load embeddings from sidecar file. Returns None if not found."""
        path = self._sidecar_path(conversation_id)
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)

    def list_embedded_conversations(self) -> list[str]:
        """List conversation IDs that have embedding sidecars."""
        ids = []
        for path in self.conversations_dir.glob("*.embeddings.json"):
            # filename is {uuid}.embeddings.json
            conv_id = path.name.replace(".embeddings.json", "")
            ids.append(conv_id)
        return ids
