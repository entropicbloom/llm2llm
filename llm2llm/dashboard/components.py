"""UI components for the dashboard."""

import streamlit as st
from .styles import (
    get_topic_color,
    get_trajectory_color,
    score_to_opacity,
    MOOD_COLORS,
)
from .data import get_provider_display_name


def render_topic_tags(topics: dict[str, float], max_topics: int = 5) -> None:
    """Render topic tags with scores."""
    if not topics:
        st.write("No topics")
        return

    # Sort by score and take top N
    sorted_topics = sorted(topics.items(), key=lambda x: -x[1])[:max_topics]

    cols = st.columns(len(sorted_topics))
    for i, (topic, score) in enumerate(sorted_topics):
        color = get_topic_color(topic)
        with cols[i]:
            st.markdown(
                f"""<span style="
                    background-color: {color};
                    padding: 4px 10px;
                    border-radius: 12px;
                    font-size: 0.8em;
                    opacity: {score_to_opacity(score)};
                ">{topic} <small>{score:.0%}</small></span>""",
                unsafe_allow_html=True,
            )


def render_mood_bars(warmth: float, energy: float, depth: float) -> None:
    """Render mood dimension bars."""
    dimensions = [
        ("Warmth", warmth, MOOD_COLORS["warmth"]),
        ("Energy", energy, MOOD_COLORS["energy"]),
        ("Depth", depth, MOOD_COLORS["depth"]),
    ]

    for name, value, color in dimensions:
        # Value is -1 to 1, convert to 0-100 for display
        # Center point is at 50%
        pct = (value + 1) / 2 * 100

        col1, col2 = st.columns([1, 3])
        with col1:
            st.caption(name)
        with col2:
            # Create a bar with the center marked
            if value >= 0:
                # Positive: bar grows from center to right
                st.markdown(
                    f"""<div style="
                        display: flex;
                        align-items: center;
                        height: 20px;
                    ">
                        <div style="width: 50%; height: 8px; background: #333; border-radius: 4px 0 0 4px;"></div>
                        <div style="width: {value * 50}%; height: 8px; background: {color}; border-radius: 0 4px 4px 0;"></div>
                        <div style="width: {50 - value * 50}%; height: 8px; background: #333; border-radius: 0 4px 4px 0;"></div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            else:
                # Negative: bar grows from center to left
                st.markdown(
                    f"""<div style="
                        display: flex;
                        align-items: center;
                        height: 20px;
                    ">
                        <div style="width: {50 + value * 50}%; height: 8px; background: #333; border-radius: 4px 0 0 4px;"></div>
                        <div style="width: {-value * 50}%; height: 8px; background: {color}; opacity: 0.7; border-radius: 4px 0 0 4px;"></div>
                        <div style="width: 50%; height: 8px; background: #333; border-radius: 0 4px 4px 0;"></div>
                    </div>""",
                    unsafe_allow_html=True,
                )


def render_trajectory_badge(trajectory: str, trajectory_dist: dict[str, int]) -> None:
    """Render trajectory with distribution."""
    if not trajectory_dist:
        st.write("No trajectory data")
        return

    # Find dominant trajectory
    dominant = max(trajectory_dist.items(), key=lambda x: x[1])[0]
    total = sum(trajectory_dist.values())
    dominant_pct = trajectory_dist[dominant] / total

    color = get_trajectory_color(dominant)
    st.markdown(
        f"""<span style="
            background-color: {color}22;
            border: 1px solid {color};
            color: {color};
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: 500;
        ">{dominant} ({dominant_pct:.0%})</span>""",
        unsafe_allow_html=True,
    )


def render_model_card(stats: dict) -> None:
    """Render a model card with all its stats."""
    model_id = stats["model_id"]
    display_name = get_provider_display_name(model_id)
    conv_count = stats["conversation_count"]

    st.subheader(f"🤖 {display_name}")
    st.caption(f"{conv_count} conversation{'s' if conv_count != 1 else ''} analyzed")

    # Topics
    st.markdown("**Topics**")
    render_topic_tags(stats["avg_topics"])

    st.markdown("")

    # Mood dimensions
    st.markdown("**Mood**")
    render_mood_bars(
        stats["avg_warmth"],
        stats["avg_energy"],
        stats["avg_depth"],
    )

    # Tone
    tone = stats["avg_tone_playful"]
    tone_label = "Playful" if tone > 0.6 else "Serious" if tone < 0.4 else "Balanced"
    st.caption(f"Tone: {tone_label} ({tone:.0%} playful)")

    st.markdown("")

    # Trajectory
    st.markdown("**Trajectory**")
    render_trajectory_badge(
        max(stats["trajectory_distribution"].items(), key=lambda x: x[1])[0] if stats["trajectory_distribution"] else "unknown",
        stats["trajectory_distribution"],
    )

    # Behavioral flags
    if stats["ending_attempt_rate"] > 0:
        st.caption(f"⚠️ Ending attempts: {stats['ending_attempt_rate']:.0%} of conversations")

    # Structure flags
    flags = []
    if stats["is_lengthy_rate"] > 0.3:
        flags.append("lengthy")
    if stats["is_structured_rate"] > 0.3:
        flags.append("structured")
    if flags:
        st.caption(f"📝 Style: {', '.join(flags)}")

    # Partner tendencies (expandable)
    if stats["partner_stats"]:
        with st.expander(f"Partner Tendencies ({len(stats['partner_stats'])} partners)"):
            for partner_id, partner_stats in stats["partner_stats"].items():
                partner_display = get_provider_display_name(partner_id)
                st.markdown(f"**With {partner_display}** ({partner_stats['count']} conv)")

                # Compact view of partner-specific stats
                if partner_stats.get("avg_topics"):
                    top_topics = list(partner_stats["avg_topics"].items())[:3]
                    topics_str = ", ".join(f"{t}({s:.0%})" for t, s in top_topics)
                    st.caption(f"Topics: {topics_str}")

                if partner_stats.get("trajectory_distribution"):
                    dominant = max(partner_stats["trajectory_distribution"].items(), key=lambda x: x[1])[0]
                    st.caption(f"→ {dominant}")

                st.markdown("---")


def render_provider_section(provider: str, models: list[str], all_stats: dict[str, dict]) -> None:
    """Render a section for a provider with all its models."""
    st.header(f"📦 {provider}")

    # Create columns for model cards
    cols = st.columns(min(len(models), 3))

    for i, model_id in enumerate(models):
        with cols[i % 3]:
            stats = all_stats.get(model_id)
            if stats and stats["conversation_count"] > 0:
                with st.container():
                    render_model_card(stats)
