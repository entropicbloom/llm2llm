"""UI components for the dashboard."""

import streamlit as st
from llm2llm.dashboard.styles import (
    get_topic_color,
    get_trajectory_color,
    score_to_opacity,
    MOOD_COLORS,
)
from llm2llm.dashboard.data import get_provider_display_name


def render_topic_tags(topics: dict[str, float], max_topics: int = 5) -> None:
    """Render topic tags with scores."""
    if not topics:
        st.caption("No topics")
        return

    # Sort by score and take top N
    sorted_topics = sorted(topics.items(), key=lambda x: -x[1])[:max_topics]

    # Build all tags as inline HTML - simple monochrome style
    tags_html = '<div class="topic-tags">'
    for topic, score in sorted_topics:
        tags_html += f'<span class="topic-tag">{topic} {score:.0%}</span>'
    tags_html += '</div>'

    st.markdown(tags_html, unsafe_allow_html=True)


def render_mood_bars(warmth: float, energy: float, depth: float) -> None:
    """Render mood dimension bars."""
    dimensions = [
        ("Warmth", warmth, MOOD_COLORS["warmth"]),
        ("Energy", energy, MOOD_COLORS["energy"]),
        ("Depth", depth, MOOD_COLORS["depth"]),
    ]

    for name, value, color in dimensions:
        # Value is -1 to 1, center at 50%
        center = 50
        if value >= 0:
            left_empty = center
            bar_width = value * 50
            bar_left = center
        else:
            bar_width = -value * 50
            bar_left = center - bar_width
            left_empty = bar_left

        st.markdown(
            f"""<div class="mood-bar-container">
                <span class="mood-label">{name}</span>
                <div class="mood-bar" style="position: relative;">
                    <div style="position: absolute; left: 50%; width: 1px; height: 100%; background: rgba(128,128,128,0.5);"></div>
                    <div style="position: absolute; left: {bar_left}%; width: {bar_width}%; height: 100%; background: {color}; border-radius: 3px;"></div>
                </div>
                <span style="width: 40px; font-size: 0.8em; opacity: 0.6;">{value:+.1f}</span>
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
            background-color: {color}33;
            border: 1px solid {color};
            color: {color};
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: 500;
        ">{dominant} ({dominant_pct:.0%})</span>""",
        unsafe_allow_html=True,
    )


def render_model_card_compact(stats: dict, provider: str) -> None:
    """Render a compact model card with expandable details."""
    model_id = stats["model_id"]
    display_name = get_provider_display_name(model_id)
    conv_count = stats["conversation_count"]

    # Get summary info
    top_topics = list(stats["avg_topics"].keys())[:2]
    topics_str = ", ".join(top_topics) if top_topics else "no topics"

    dominant_traj = max(stats["trajectory_distribution"].items(), key=lambda x: x[1])[0] if stats["trajectory_distribution"] else "unknown"
    traj_color = get_trajectory_color(dominant_traj)

    # Compact header with key info
    with st.expander(f"**{display_name}** | {conv_count} convs | {topics_str} | {dominant_traj}"):
        # Full details inside expander

        # Topics
        st.markdown("**Topics**")
        render_topic_tags(stats["avg_topics"])

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

        # Trajectory
        st.markdown("**Trajectory**")
        render_trajectory_badge(dominant_traj, stats["trajectory_distribution"])

        # Behavioral flags
        if stats["ending_attempt_rate"] > 0:
            st.caption(f"Ending attempts: {stats['ending_attempt_rate']:.0%} of conversations")

        # Structure flags
        flags = []
        if stats["is_lengthy_rate"] > 0.3:
            flags.append("lengthy")
        if stats["is_structured_rate"] > 0.3:
            flags.append("structured")
        if flags:
            st.caption(f"Style: {', '.join(flags)}")

        # Partner tendencies
        if stats["partner_stats"]:
            st.markdown("**Partner Tendencies**")
            for partner_id, partner_stats in stats["partner_stats"].items():
                partner_display = get_provider_display_name(partner_id)

                partner_topics = list(partner_stats.get("avg_topics", {}).keys())[:2]
                partner_topics_str = ", ".join(partner_topics) if partner_topics else ""

                partner_traj = ""
                if partner_stats.get("trajectory_distribution"):
                    partner_traj = max(partner_stats["trajectory_distribution"].items(), key=lambda x: x[1])[0]

                st.caption(f"With {partner_display} ({partner_stats['count']}): {partner_topics_str} | {partner_traj}")


def render_models_grid(all_stats: dict[str, dict], providers: dict[str, list[str]]) -> None:
    """Render all models as compact expandable cards with filtering."""
    from llm2llm.dashboard.data import infer_provider

    st.header("Models")

    # Filter controls
    col1, col2 = st.columns(2)

    provider_list = ["All"] + sorted(providers.keys())
    with col1:
        selected_provider = st.selectbox("Filter by Provider", provider_list)

    # Get all models with stats
    models_with_stats = [
        (model_id, stats, infer_provider(model_id))
        for model_id, stats in all_stats.items()
        if stats["conversation_count"] > 0
    ]

    # Apply provider filter
    if selected_provider != "All":
        models_with_stats = [
            (m, s, p) for m, s, p in models_with_stats
            if p == selected_provider
        ]

    # Sort options
    sort_options = {
        "Conversations": lambda x: -x[1]["conversation_count"],
        "Depth": lambda x: -x[1]["avg_depth"],
        "Warmth": lambda x: -x[1]["avg_warmth"],
        "Energy": lambda x: -x[1]["avg_energy"],
        "Name": lambda x: x[0],
    }

    with col2:
        sort_by = st.selectbox("Sort by", list(sort_options.keys()))

    models_with_stats.sort(key=sort_options[sort_by])

    st.caption(f"Showing {len(models_with_stats)} models")

    # Render compact cards
    for model_id, stats, provider in models_with_stats:
        render_model_card_compact(stats, provider)


def render_pair_rankings(pair_stats: list[dict]) -> None:
    """Render model pair rankings with sortable attributes."""
    st.header("Model Pair Rankings")

    if not pair_stats:
        st.info("No pair data to display")
        return

    # Attribute selector
    attributes = {
        "Conversations": ("conversation_count", False, "{:.0f}"),
        "Depth": ("avg_depth", False, "{:+.2f}"),
        "Warmth": ("avg_warmth", False, "{:+.2f}"),
        "Energy": ("avg_energy", False, "{:+.2f}"),
        "Playfulness": ("avg_tone_playful", False, "{:.0%}"),
        "Ending Attempts": ("ending_attempt_rate", False, "{:.0%}"),
        "Lengthy": ("is_lengthy_rate", False, "{:.0%}"),
        "Structured": ("is_structured_rate", False, "{:.0%}"),
        "Avg Turns": ("avg_turns", False, "{:.1f}"),
    }

    col1, col2 = st.columns([2, 1])
    with col1:
        sort_by = st.selectbox(
            "Rank by",
            list(attributes.keys()),
            index=1,  # Default to Depth
        )
    with col2:
        ascending = st.checkbox("Ascending", value=False)

    attr_key, _, fmt = attributes[sort_by]

    # Sort pairs
    sorted_pairs = sorted(
        pair_stats,
        key=lambda x: x.get(attr_key, 0),
        reverse=not ascending,
    )

    # Display rankings
    for rank, pair in enumerate(sorted_pairs, 1):
        llm1_display = get_provider_display_name(pair["llm1"])
        llm2_display = get_provider_display_name(pair["llm2"])
        value = pair.get(attr_key, 0)
        formatted_value = fmt.format(value)

        # Get top topics for context
        top_topics = list(pair.get("avg_topics", {}).keys())[:3]
        topics_str = ", ".join(top_topics) if top_topics else "no topics"

        col1, col2, col3 = st.columns([1, 4, 2])

        with col1:
            st.markdown(f"**#{rank}**")

        with col2:
            st.markdown(f"**{llm1_display}** + **{llm2_display}**")
            st.caption(f"{pair['conversation_count']} convs | {pair['dominant_trajectory']} | {topics_str}")

        with col3:
            st.markdown(f"**{formatted_value}**")
            st.caption(sort_by)

        st.markdown("---")


def render_conversation_browser(analyses: list[dict], conversations_dir) -> None:
    """Render a conversation browser with filtering and transcript viewing."""
    from pathlib import Path
    from llm2llm.dashboard.data import load_conversation

    st.header("Conversation Browser")

    if not analyses:
        st.info("No conversations to display")
        return

    # Filters
    col1, col2, col3 = st.columns(3)

    # Get unique values for filters
    all_models = sorted(set(
        m for a in analyses for m in [a["llm1_model"], a["llm2_model"]]
    ))
    all_trajectories = sorted(set(a.get("trajectory", "unknown") for a in analyses))
    all_topics = sorted(set(
        t for a in analyses for t in a.get("topics", {}).keys()
    ))

    with col1:
        model_filter = st.selectbox(
            "Filter by Model",
            ["All"] + all_models,
            format_func=lambda x: x if x == "All" else get_provider_display_name(x)
        )

    with col2:
        trajectory_filter = st.selectbox(
            "Filter by Trajectory",
            ["All"] + all_trajectories
        )

    with col3:
        topic_filter = st.selectbox(
            "Filter by Topic",
            ["All"] + all_topics
        )

    # Apply filters
    filtered = analyses
    if model_filter != "All":
        filtered = [a for a in filtered if model_filter in [a["llm1_model"], a["llm2_model"]]]
    if trajectory_filter != "All":
        filtered = [a for a in filtered if a.get("trajectory") == trajectory_filter]
    if topic_filter != "All":
        filtered = [a for a in filtered if topic_filter in a.get("topics", {})]

    st.caption(f"Showing {len(filtered)} of {len(analyses)} conversations")

    # Conversation list
    for a in filtered[:20]:  # Limit to 20 for performance
        conv_id = a["conversation_id"]
        llm1 = get_provider_display_name(a["llm1_model"])
        llm2 = get_provider_display_name(a["llm2_model"])
        trajectory = a.get("trajectory", "unknown")
        traj_color = get_trajectory_color(trajectory)

        # Summary line with topics
        topics = a.get("topics", {})
        top_topics = ", ".join(list(topics.keys())[:3]) if topics else "no topics"

        # Ending indicator
        ending = ""
        if a.get("ending_attempt"):
            ending = " [ended]" if a.get("ending_graceful") else " [ended awkwardly]"

        with st.expander(f"{llm1} / {llm2} | {trajectory}{ending} | {top_topics}"):
            # Analysis summary
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Analysis**")
                render_topic_tags(topics, max_topics=5)
                st.caption(f"Warmth: {a.get('warmth', 0):+.1f} | Energy: {a.get('energy', 0):+.1f} | Depth: {a.get('depth', 0):+.1f}")

            with col2:
                st.markdown("**Metadata**")
                st.caption(f"ID: `{conv_id[:8]}...`")
                st.caption(f"Turns: {a.get('turn_count', '?')}")
                tone = a.get("tone_playful", 0.5)
                st.caption(f"Tone: {'playful' if tone > 0.6 else 'serious' if tone < 0.4 else 'balanced'}")

            # Load and show transcript
            st.markdown("---")
            st.markdown("**Transcript**")

            conv_data = load_conversation(Path(conversations_dir), conv_id)
            if conv_data and "messages" in conv_data:
                messages = conv_data["messages"]

                # Show message count and option to limit
                total_msgs = len(messages)
                show_all = st.checkbox(f"Show all {total_msgs} messages", key=f"show_all_{conv_id}", value=False)

                if show_all:
                    display_msgs = messages
                else:
                    # Show first 3 and last 5
                    if total_msgs <= 8:
                        display_msgs = messages
                    else:
                        display_msgs = messages[:3] + [{"_separator": True}] + messages[-5:]

                for i, msg in enumerate(display_msgs):
                    if msg.get("_separator"):
                        st.caption(f"... ({total_msgs - 8} messages hidden) ...")
                        continue

                    role = msg.get("participant_role", "unknown")
                    content = msg.get("content", "")

                    # Color code by role
                    if role == "initiator":
                        st.markdown(f"**{llm1}:**")
                    else:
                        st.markdown(f"*{llm2}:*")

                    st.markdown(content[:1000] + ("..." if len(content) > 1000 else ""))
                    st.markdown("")
            else:
                st.warning("Transcript not available")
