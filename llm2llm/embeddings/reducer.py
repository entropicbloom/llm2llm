"""Dimensionality reduction for conversation embeddings (UMAP/PCA to 2D)."""

import json
from pathlib import Path

import numpy as np

from .storage import EmbeddingStorage


def reduce_embeddings(
    conversations_dir: Path,
    method: str = "umap",
    n_components: int = 2,
) -> dict:
    """Reduce all conversation embeddings to 2D coordinates.

    Fits a single reduction model across ALL conversations at once so that
    coordinates are comparable across conversations.

    Args:
        conversations_dir: Path to conversations/ directory containing sidecar files.
        method: "umap" or "pca".
        n_components: Number of output dimensions (default 2).

    Returns:
        Dict with conversation IDs as keys, each containing a list of points:
        {
            "conv-uuid": {
                "llm1_model": "...",
                "llm2_model": "...",
                "points": [
                    {"turn": 1, "role": "initiator", "x": 0.5, "y": -0.3},
                    ...
                ]
            },
            ...
        }
    """
    storage = EmbeddingStorage(conversations_dir)
    conv_ids = storage.list_embedded_conversations()

    if not conv_ids:
        return {}

    # Collect all embeddings into a single matrix, tracking provenance
    all_vectors = []
    metadata = []  # (conv_id, turn_number, participant_role) per row

    # Also load conversation JSON to get model info
    conv_models = {}

    for conv_id in sorted(conv_ids):
        emb_data = storage.load_embeddings(conv_id)
        if not emb_data or not emb_data.get("messages"):
            continue

        # Load conversation JSON for model info
        conv_path = conversations_dir / f"{conv_id}.json"
        if conv_path.exists():
            with open(conv_path) as f:
                conv_json = json.load(f)
            conv_models[conv_id] = {
                "llm1_model": conv_json.get("llm1_model", "unknown"),
                "llm2_model": conv_json.get("llm2_model", "unknown"),
            }
        else:
            conv_models[conv_id] = {
                "llm1_model": "unknown",
                "llm2_model": "unknown",
            }

        for msg in emb_data["messages"]:
            all_vectors.append(msg["embedding"])
            metadata.append((conv_id, msg["turn_number"], msg["participant_role"]))

    if not all_vectors:
        return {}

    matrix = np.array(all_vectors, dtype=np.float32)

    # Reduce
    if method == "umap":
        coords_2d = _reduce_umap(matrix, n_components)
    elif method == "pca":
        coords_2d = _reduce_pca(matrix, n_components)
    else:
        raise ValueError(f"Unknown method: {method}. Use 'umap' or 'pca'.")

    # Normalize to [-1, 1]
    for dim in range(n_components):
        col = coords_2d[:, dim]
        col_min, col_max = col.min(), col.max()
        if col_max - col_min > 0:
            coords_2d[:, dim] = 2 * (col - col_min) / (col_max - col_min) - 1
        else:
            coords_2d[:, dim] = 0.0

    # Group by conversation
    result = {}
    for i, (conv_id, turn, role) in enumerate(metadata):
        if conv_id not in result:
            result[conv_id] = {
                **conv_models.get(conv_id, {"llm1_model": "unknown", "llm2_model": "unknown"}),
                "points": [],
            }
        result[conv_id]["points"].append({
            "turn": turn,
            "role": role,
            "x": round(float(coords_2d[i, 0]), 4),
            "y": round(float(coords_2d[i, 1]), 4),
        })

    return result


def _reduce_umap(matrix: np.ndarray, n_components: int) -> np.ndarray:
    """Try UMAP, fall back to PCA if unavailable."""
    try:
        import umap
        reducer = umap.UMAP(
            n_components=n_components,
            metric="cosine",
            random_state=42,
        )
        return reducer.fit_transform(matrix)
    except ImportError:
        print("umap-learn not installed, falling back to PCA")
        return _reduce_pca(matrix, n_components)


def _reduce_pca(matrix: np.ndarray, n_components: int) -> np.ndarray:
    """PCA reduction via scikit-learn."""
    from sklearn.decomposition import PCA
    reducer = PCA(n_components=n_components, random_state=42)
    return reducer.fit_transform(matrix)
