"""Main Streamlit dashboard app."""

import sys
from pathlib import Path

# Add parent directories to path for Streamlit direct execution
_this_file = Path(__file__).resolve()
_dashboard_dir = _this_file.parent
_llm2llm_dir = _dashboard_dir.parent
_project_dir = _llm2llm_dir.parent

if str(_project_dir) not in sys.path:
    sys.path.insert(0, str(_project_dir))

import streamlit as st

from llm2llm.dashboard.data import (
    load_all_analyses,
    get_models_by_provider,
    aggregate_model_stats,
    aggregate_pair_stats,
)
from llm2llm.dashboard.components import render_models_grid, render_conversation_browser, render_pair_rankings
from llm2llm.dashboard.styles import CUSTOM_CSS


def get_db_path() -> Path:
    """Get the database path from config or default."""
    # Try to find the database
    possible_paths = [
        Path("data/llm2llm.db"),
        Path.home() / ".llm2llm" / "llm2llm.db",
        Path(__file__).parent.parent.parent / "data" / "llm2llm.db",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    # Default path
    return Path("data/llm2llm.db")


def run_dashboard() -> None:
    """Main dashboard entry point."""
    st.set_page_config(
        page_title="LLM2LLM Analysis",
        page_icon="🤖",
        layout="wide",
    )

    # Inject custom CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    st.title("LLM2LLM Analysis Dashboard")
    st.caption("Analyzing conversation patterns between AI models")

    # Load data
    db_path = get_db_path()

    if not db_path.exists():
        st.error(f"Database not found at {db_path}")
        st.info("Run some conversations first with `llm2llm batch` and analyze them with `llm2llm analyze`")
        return

    try:
        all_analyses = load_all_analyses(db_path)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return

    if not all_analyses:
        st.warning("No analysis data found. Run `llm2llm analyze` to analyze completed conversations.")
        return

    # Extract unique segments
    segments = sorted(set(
        (a["segment_start"], a["segment_end"])
        for a in all_analyses
    ))

    # Segment selector in sidebar
    st.sidebar.header("Analysis Settings")

    def format_segment(seg: tuple) -> str:
        start, end = seg
        if end is None:
            return f"Messages [{start}:] (last {-start})"
        return f"Messages [{start}:{end}]"

    segment_options = [format_segment(s) for s in segments]
    selected_idx = st.sidebar.selectbox(
        "Conversation Segment",
        range(len(segments)),
        format_func=lambda i: segment_options[i],
        help="Which part of conversations to analyze"
    )
    selected_segment = segments[selected_idx]

    # Filter analyses by selected segment
    analyses = [
        a for a in all_analyses
        if (a["segment_start"], a["segment_end"]) == selected_segment
    ]

    # Get models grouped by provider
    providers = get_models_by_provider(analyses)

    # Compute stats for all models
    all_models = set()
    for models in providers.values():
        all_models.update(models)

    all_stats = {
        model_id: aggregate_model_stats(analyses, model_id)
        for model_id in all_models
    }

    # Summary stats
    total_conversations = len(set(a["conversation_id"] for a in analyses))
    total_models = len(all_models)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Conversations", total_conversations)
    with col2:
        st.metric("Models Analyzed", total_models)
    with col3:
        st.metric("Providers", len(providers))

    st.markdown("---")

    # Main view tabs: Models vs Rankings vs Conversations
    main_tab1, main_tab2, main_tab3 = st.tabs(["Models", "Rankings", "Conversations"])

    with main_tab1:
        render_models_grid(all_stats, providers)

    with main_tab2:
        # Pair rankings
        pair_stats = aggregate_pair_stats(analyses)
        render_pair_rankings(pair_stats)

    with main_tab3:
        # Conversation browser
        conversations_dir = db_path.parent.parent / "conversations"
        render_conversation_browser(analyses, conversations_dir)


# Allow running directly with streamlit
if __name__ == "__main__":
    run_dashboard()
