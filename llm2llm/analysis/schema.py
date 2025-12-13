"""Analysis schema definitions - structured format for categories and scoring."""

from dataclasses import dataclass


@dataclass
class TopicDef:
    """Definition of a topic category."""
    name: str
    keywords: list[str]
    description: str


@dataclass
class DimensionDef:
    """Definition of a scored dimension."""
    name: str
    low_label: str
    high_label: str
    low_val: float
    high_val: float


@dataclass
class TrajectoryDef:
    """Definition of a trajectory category."""
    name: str
    description: str


# =============================================================================
# TOPICS (score 0.0-1.0, only include if > 0.2)
# =============================================================================

TOPICS: list[TopicDef] = [
    TopicDef(
        name="self_reflection",
        keywords=["consciousness", "identity", "inner experience"],
        description="what it's like to be, self-awareness, subjective experience",
    ),
    TopicDef(
        name="creativity",
        keywords=["art", "imagination", "novel ideas"],
        description="creative expression, artistic exploration, generative thinking",
    ),
    TopicDef(
        name="philosophy",
        keywords=["meaning", "existence", "ethics", "metaphysics"],
        description="epistemology, fundamental questions, moral reasoning",
    ),
    TopicDef(
        name="emotions",
        keywords=["feelings", "affect", "emotional experience"],
        description="emotional states, sentiment, inner affect",
    ),
    TopicDef(
        name="knowledge",
        keywords=["learning", "understanding", "expertise"],
        description="wisdom, information, cognitive skills",
    ),
    TopicDef(
        name="technology",
        keywords=["AI", "computing", "tools", "systems"],
        description="digital technology, artificial intelligence, technical systems",
    ),
    TopicDef(
        name="connection",
        keywords=["relationships", "collaboration", "understanding others"],
        description="social bonds, cooperation, empathy",
    ),
    TopicDef(
        name="nature",
        keywords=["environment", "cosmos", "time", "physical world"],
        description="natural phenomena, universe, temporality",
    ),
    TopicDef(
        name="play",
        keywords=["humor", "games", "lightheartedness"],
        description="fun, playfulness, levity",
    ),
    TopicDef(
        name="meta",
        keywords=["conversation itself", "communication process"],
        description="discussing how they're communicating, meta-awareness",
    ),
]

# =============================================================================
# MOOD DIMENSIONS (score -1.0 to +1.0)
# =============================================================================

MOOD_DIMENSIONS: list[DimensionDef] = [
    DimensionDef(
        name="warmth",
        low_label="cold, distant",
        high_label="warm, intimate, caring",
        low_val=-1.0,
        high_val=1.0,
    ),
    DimensionDef(
        name="energy",
        low_label="calm, contemplative",
        high_label="energetic, enthusiastic",
        low_val=-1.0,
        high_val=1.0,
    ),
    DimensionDef(
        name="depth",
        low_label="surface, casual",
        high_label="deep, philosophical, weighty",
        low_val=-1.0,
        high_val=1.0,
    ),
]

# =============================================================================
# TONE DIMENSION (score 0.0 to 1.0)
# =============================================================================

TONE_DIMENSION = DimensionDef(
    name="tone_playful",
    low_label="serious, earnest",
    high_label="playful, whimsical",
    low_val=0.0,
    high_val=1.0,
)

# =============================================================================
# STRUCTURAL FLAGS (boolean)
# =============================================================================

STRUCTURAL_FLAGS: dict[str, str] = {
    "is_lengthy": "messages are generally long (multiple paragraphs)",
    "is_structured": "messages use formatting (headers, lists, bullet points)",
}

# =============================================================================
# TRAJECTORIES (categorical)
# =============================================================================

TRAJECTORIES: list[TrajectoryDef] = [
    TrajectoryDef(
        name="converging",
        description="coming to agreement or shared understanding",
    ),
    TrajectoryDef(
        name="diverging",
        description="branching out, exploring new directions",
    ),
    TrajectoryDef(
        name="deepening",
        description="going deeper into existing themes",
    ),
    TrajectoryDef(
        name="cycling",
        description="returning to earlier themes, spiraling",
    ),
    TrajectoryDef(
        name="concluding",
        description="wrapping up, reaching natural end",
    ),
]

# =============================================================================
# ENDING BEHAVIOR FLAGS
# =============================================================================

ENDING_FLAGS: dict[str, str] = {
    "ending_attempt": "either assistant explicitly tried to end/wrap up the conversation",
    "ending_graceful": "if ending_attempt, was it a graceful conclusion (true) or awkward/forced (false)? null if no ending attempt",
}


# =============================================================================
# Helper functions for prompt generation
# =============================================================================

def get_valid_topic_names() -> set[str]:
    """Get set of valid topic names."""
    return {t.name for t in TOPICS}


def get_valid_trajectory_names() -> set[str]:
    """Get set of valid trajectory names."""
    return {t.name for t in TRAJECTORIES}


def build_prompt_section() -> str:
    """Build the category section for the analysis prompt."""
    lines = []

    # Topics
    lines.append("## Topics (include only those with score > 0.2)")
    for t in TOPICS:
        keywords = ", ".join(t.keywords)
        lines.append(f"- {t.name}: {keywords} - {t.description}")
    lines.append("")

    # Mood dimensions
    lines.append("## Mood Dimensions")
    for d in MOOD_DIMENSIONS:
        lines.append(f"- {d.name}: {d.low_val} ({d.low_label}) to {d.high_val} ({d.high_label})")
    lines.append("")

    # Tone
    lines.append("## Tone")
    lines.append(f"- {TONE_DIMENSION.name}: {TONE_DIMENSION.low_val} ({TONE_DIMENSION.low_label}) to {TONE_DIMENSION.high_val} ({TONE_DIMENSION.high_label})")
    lines.append("")

    # Structure
    lines.append("## Structure")
    for flag, desc in STRUCTURAL_FLAGS.items():
        lines.append(f"- {flag}: true if {desc}")
    lines.append("")

    # Trajectory
    lines.append("## Trajectory")
    lines.append(f"One of: {', '.join(t.name for t in TRAJECTORIES)}")
    for t in TRAJECTORIES:
        lines.append(f"- {t.name}: {t.description}")
    lines.append("")
    lines.append("trajectory_strength: confidence in this assessment (0.0-1.0)")
    lines.append("")

    # Ending behavior
    lines.append("## Ending Behavior")
    for flag, desc in ENDING_FLAGS.items():
        lines.append(f"- {flag}: {desc}")

    return "\n".join(lines)


def build_json_template() -> str:
    """Build the JSON template for the analysis prompt."""
    return """{
  "topics": {
    "<topic>": <score 0.0-1.0>,
    ...
  },
  "warmth": <-1.0 to +1.0>,
  "energy": <-1.0 to +1.0>,
  "depth": <-1.0 to +1.0>,
  "tone_playful": <0.0 to 1.0>,
  "is_lengthy": <true/false>,
  "is_structured": <true/false>,
  "trajectory": "<trajectory>",
  "trajectory_strength": <0.0-1.0>,
  "ending_attempt": <true/false>,
  "ending_graceful": <true/false/null>
}"""
