"""Styling constants and CSS for the dashboard."""

# Provider colors
PROVIDER_COLORS = {
    "Anthropic": "#D97757",  # Coral/orange
    "Mistral": "#4A90D9",    # Blue
    "OpenAI": "#10A37F",     # Green
    "Google": "#4285F4",     # Google blue
    "Other": "#888888",      # Gray
}

# Topic colors (for consistent color coding)
TOPIC_COLORS = {
    "self_reflection": "#9B59B6",  # Purple
    "creativity": "#E74C3C",       # Red
    "philosophy": "#3498DB",       # Blue
    "emotions": "#E91E63",         # Pink
    "knowledge": "#2ECC71",        # Green
    "technology": "#00BCD4",       # Cyan
    "connection": "#FF9800",       # Orange
    "nature": "#4CAF50",           # Forest green
    "play": "#FFEB3B",             # Yellow
    "meta": "#607D8B",             # Blue-gray
}

# Trajectory colors
TRAJECTORY_COLORS = {
    "converging": "#27AE60",   # Green
    "diverging": "#E74C3C",    # Red
    "deepening": "#3498DB",    # Blue
    "cycling": "#F39C12",      # Orange
    "concluding": "#9B59B6",   # Purple
    "unknown": "#888888",      # Gray
}

# Mood dimension colors
MOOD_COLORS = {
    "warmth": "#FF6B6B",  # Warm red
    "energy": "#4ECDC4",  # Energetic teal
    "depth": "#45B7D1",   # Deep blue
}

# CSS for custom styling
CUSTOM_CSS = """
<style>
    .model-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid #333;
    }

    .partner-card {
        background: #0d1117;
        border-radius: 8px;
        padding: 12px;
        margin: 5px 0;
        border: 1px solid #21262d;
    }

    .topic-tag {
        display: inline-block;
        padding: 4px 12px;
        margin: 2px;
        border-radius: 16px;
        font-size: 0.85em;
        font-weight: 500;
    }

    .mood-bar {
        height: 8px;
        border-radius: 4px;
        margin: 4px 0;
    }

    .stat-number {
        font-size: 2em;
        font-weight: bold;
        color: #fff;
    }

    .stat-label {
        font-size: 0.85em;
        color: #888;
        text-transform: uppercase;
    }

    .trajectory-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 4px;
        font-weight: 500;
    }
</style>
"""


def get_topic_color(topic: str) -> str:
    """Get color for a topic."""
    return TOPIC_COLORS.get(topic, "#888888")


def get_trajectory_color(trajectory: str) -> str:
    """Get color for a trajectory."""
    return TRAJECTORY_COLORS.get(trajectory, "#888888")


def get_provider_color(provider: str) -> str:
    """Get color for a provider."""
    return PROVIDER_COLORS.get(provider, "#888888")


def mood_to_color(value: float, dimension: str) -> str:
    """Convert mood dimension value to a color with opacity."""
    base_color = MOOD_COLORS.get(dimension, "#888888")
    # Value is -1 to 1, convert to 0-1 for opacity
    opacity = (value + 1) / 2
    return f"{base_color}{int(opacity * 255):02x}"


def score_to_opacity(score: float) -> float:
    """Convert 0-1 score to opacity (0.3-1.0)."""
    return 0.3 + (score * 0.7)
