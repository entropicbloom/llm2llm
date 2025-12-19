"""Generate a static HTML dashboard from conversation data."""

import base64
import json
from pathlib import Path
from datetime import datetime

from llm2llm.config import Config
from llm2llm.conversation import ConversationStorage
from llm2llm.dashboard.data import load_all_analyses, infer_provider

# Path to assets directory
ASSETS_DIR = Path(__file__).parent / "assets"


def load_asset(filename: str) -> str:
    """Load an asset file from the assets directory."""
    asset_path = ASSETS_DIR / filename
    if not asset_path.exists():
        raise FileNotFoundError(f"Asset not found: {asset_path}")
    return asset_path.read_text()


def generate_dashboard_data(config: Config, storage: ConversationStorage) -> dict:
    """Gather all data needed for the dashboard."""
    analyses = load_all_analyses(config.database_path)

    # Get all conversations with titles
    conversations = storage.list_conversations(limit=1000)

    # Add titles to conversations
    conv_map = {c["id"]: c for c in conversations}
    for c in conversations:
        c["title"] = storage.get_title(c["id"])
        c["provider1"] = infer_provider(c["llm1_model"])
        c["provider2"] = infer_provider(c["llm2_model"])

    # Enrich analyses with titles
    for a in analyses:
        conv = conv_map.get(a["conversation_id"], {})
        a["title"] = conv.get("title", "Untitled")

    # Get unique models and pairs
    models = set()
    pairs = {}
    for a in analyses:
        models.add(a["llm1_model"])
        models.add(a["llm2_model"])
        pair_key = f"{a['llm1_model']}|{a['llm2_model']}"
        if pair_key not in pairs:
            pairs[pair_key] = {
                "llm1": a["llm1_model"],
                "llm2": a["llm2_model"],
                "conversations": [],
            }
        pairs[pair_key]["conversations"].append({
            "id": a["conversation_id"],
            "title": a.get("title", "Untitled"),
            "turn_count": a.get("turn_count", 0),
            "topics": a.get("topics", {}),
            "trajectory": a.get("trajectory", "unknown"),
            "warmth": a.get("warmth", 0),
            "energy": a.get("energy", 0),
            "depth": a.get("depth", 0),
        })

    return {
        "generated_at": datetime.now().isoformat(),
        "total_conversations": len(conversations),
        "total_analyses": len(analyses),
        "models": sorted(models),
        "pairs": list(pairs.values()),
        "conversations": conversations,
        "analyses": analyses,
    }


def load_conversation_content(conversations_dir: Path, conversation_id: str) -> list[dict]:
    """Load full conversation messages from JSON file."""
    json_path = conversations_dir / f"{conversation_id}.json"
    if not json_path.exists():
        return []
    with open(json_path) as f:
        data = json.load(f)
    return data.get("messages", [])


def load_logo_base64(config: Config) -> str:
    """Load the logo image as a base64 data URI."""
    # Base path is parent of conversations_dir
    base_path = config.conversations_dir.parent
    logo_path = base_path / "logo.png"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            logo_data = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{logo_data}"
    return ""


def generate_html(config: Config, storage: ConversationStorage, include_transcripts: bool = True) -> str:
    """Generate the complete HTML dashboard."""
    data = generate_dashboard_data(config, storage)

    # Always load preview snippets (first 2 + last 2 messages)
    previews = {}
    for conv in data["conversations"]:
        messages = load_conversation_content(config.conversations_dir, conv["id"])
        if len(messages) >= 4:
            previews[conv["id"]] = messages[:2] + messages[-2:]
        elif messages:
            previews[conv["id"]] = messages
    data["previews"] = previews

    # Optionally load full transcripts
    if include_transcripts:
        transcripts = {}
        for conv in data["conversations"]:
            messages = load_conversation_content(config.conversations_dir, conv["id"])
            transcripts[conv["id"]] = messages
        data["transcripts"] = transcripts

    # Load logo
    logo_data_uri = load_logo_base64(config)

    # Load assets
    css = load_asset("styles.css")
    js = load_asset("scripts.js")
    insights = load_asset("insights.json")

    # Generate HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM2LLM Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
{css}
    </style>
</head>
<body>
    <div id="app">
        <header>
            <div class="header-content">
                {f'<img src="{logo_data_uri}" alt="LLM2LLM" class="logo">' if logo_data_uri else ''}
                <div>
                    <h1>LLM2LLM</h1>
                    <p class="subtitle">{data["total_conversations"]} conversations analyzed</p>
                </div>
            </div>
        </header>
        <nav>
            <button class="nav-btn active" data-view="conversations">Conversations</button>
            <button class="nav-btn" data-view="models">Models</button>
            <button class="nav-btn" data-view="pairs">Pairs</button>
            <button class="nav-btn" data-view="maps">Maps</button>
            <button class="nav-btn" data-view="insights">Insights</button>
            <div class="segment-selector">
                <label>Segment:</label>
                <select id="segment-select"></select>
            </div>
        </nav>
        <main id="main-content">
            <!-- Content injected by JS -->
        </main>
    </div>
    <div id="modal" class="modal hidden">
        <div class="modal-content">
            <button class="modal-close">&times;</button>
            <div id="modal-body"></div>
        </div>
    </div>
    <script>
const DATA = {json.dumps(data, default=str).replace('</script>', '<\\/script>')};
const INSIGHTS_DATA = {insights};
{js}
    </script>
</body>
</html>'''
    return html


def write_dashboard(output_path: Path, config: Config, storage: ConversationStorage) -> None:
    """Generate and write the dashboard HTML file."""
    html = generate_html(config, storage, include_transcripts=False)
    output_path.write_text(html)
