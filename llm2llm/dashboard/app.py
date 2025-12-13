"""Main Streamlit dashboard app."""

import streamlit as st
from pathlib import Path

from .data import (
    load_all_analyses,
    get_models_by_provider,
    aggregate_model_stats,
)
from .components import render_provider_section
from .styles import CUSTOM_CSS, PROVIDER_COLORS


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

    st.title("🤖 LLM2LLM Analysis Dashboard")
    st.caption("Analyzing conversation patterns between AI models")

    # Load data
    db_path = get_db_path()

    if not db_path.exists():
        st.error(f"Database not found at {db_path}")
        st.info("Run some conversations first with `llm2llm batch` and analyze them with `llm2llm analyze`")
        return

    try:
        analyses = load_all_analyses(db_path)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return

    if not analyses:
        st.warning("No analysis data found. Run `llm2llm analyze` to analyze completed conversations.")
        return

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

    # Provider tabs
    provider_list = list(providers.keys())

    if len(provider_list) == 0:
        st.warning("No data to display")
        return

    tabs = st.tabs([
        f"{p} ({len(providers[p])} models)" for p in provider_list
    ])

    for tab, provider in zip(tabs, provider_list):
        with tab:
            render_provider_section(
                provider,
                providers[provider],
                all_stats,
            )


# Allow running directly with streamlit
if __name__ == "__main__":
    run_dashboard()
