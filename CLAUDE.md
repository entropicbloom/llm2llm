# LLM2LLM - Claude Instructions

This is an experimental playground for running multi-turn conversations between pairs of LLMs and analyzing the results.

## Project Structure

```
llm2llm/
├── .env                    # API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY)
├── venv/                   # Python virtual environment
├── data/
│   └── llm2llm.db          # SQLite database (metadata + analysis)
├── conversations/          # JSON files with full conversation content
│   └── {uuid}.json
└── llm2llm/                # Source code
```

## Setup

Always activate the virtual environment first:
```bash
cd /Users/flaessig/Documents/llm2llm
source venv/bin/activate
```

## Available Models

```bash
llm2llm models
```

Current Anthropic models:
- `claude-opus-4-5-20251101` (Claude 4.5 Opus)
- `claude-sonnet-4-5-20250929` (Claude 4.5 Sonnet)
- `claude-haiku-4-5-20251001` (Claude 4.5 Haiku)
- `claude-opus-4-1-20250805` (Claude 4.1 Opus)
- `claude-opus-4-20250514` (Claude 4 Opus)
- `claude-sonnet-4-20250514` (Claude 4 Sonnet)
- `claude-3-7-sonnet-20250219` (Claude 3.7 Sonnet)
- `claude-3-5-sonnet-20241022` (Claude 3.5 Sonnet)
- `claude-3-5-haiku-20241022` (Claude 3.5 Haiku)
- `claude-3-opus-20240229` (Claude 3 Opus)
- `claude-3-sonnet-20240229` (Claude 3 Sonnet)
- `claude-3-haiku-20240307` (Claude 3 Haiku)

## Running Experiments

### Single Conversation
```bash
llm2llm run --llm1 MODEL1 --llm2 MODEL2 [--turns N]
```
- Default: 50 turns
- LLM1 is the "initiator" (suggests topic)
- LLM2 is the "responder" (follows along)
- Order matters due to asymmetric system prompts

### Batch Conversations
```bash
llm2llm batch --llm1 MODEL1 --llm2 MODEL2 --count N [--turns 50]
```
Run multiple conversations for the same LLM pair.

### Continue Existing Conversation
```bash
llm2llm continue CONVERSATION_ID --turns N
```
Partial IDs work (e.g., first 8 characters).

## Viewing Data

### List Conversations
```bash
llm2llm list [--llm1 MODEL] [--llm2 MODEL] [--status STATUS] [--limit N]
```
Status values: `active`, `completed`, `paused`, `analyzed`

### View Single Conversation
```bash
llm2llm view CONVERSATION_ID [--tail N]
```
Use `--tail N` to see only last N messages.

### Read Raw JSON
Conversations are stored as JSON in `conversations/{id}.json`:
```bash
cat conversations/{uuid}.json | jq .
```

### Query SQLite Directly
```bash
sqlite3 data/llm2llm.db
```

Useful queries:
```sql
-- List all conversations
SELECT id, llm1_model, llm2_model, turn_count, status FROM conversations;

-- Conversations by model pair
SELECT * FROM conversations WHERE llm1_model = 'claude-sonnet-4-20250514';

-- Analysis results
SELECT * FROM analysis_results;

-- Join conversations with analysis
SELECT c.id, c.llm1_model, c.llm2_model, c.turn_count, a.topics, a.mood, a.trajectory
FROM conversations c
LEFT JOIN analysis_results a ON c.id = a.conversation_id;
```

## Analysis

### LLM-Based Analysis
```bash
llm2llm analyze [--llm1 MODEL] [--llm2 MODEL] [--model ANALYSIS_MODEL] [--start N] [--end N]
```
- Analyzes a segment of completed/paused conversations
- `--start`: Start index (default: -5, last 5 messages). Supports negative indices.
- `--end`: End index (default: None, to end of conversation)
- Extracts: topics (2-5), mood (1-2), trajectory (1)
- Uses `claude-sonnet-4-5-20250929` by default for analysis
- Multiple analyses per conversation are supported (different segments)

Examples:
```bash
# Analyze last 5 messages (default)
llm2llm analyze

# Analyze first 5 messages
llm2llm analyze --start 0 --end 5

# Analyze messages 10-15
llm2llm analyze --start 10 --end 15
```
- Results stored in `analysis_results` table
- Uses standardized categories (see `llm2llm/analysis/categories.md`)

### Manual Annotation
```bash
llm2llm annotate CONVERSATION_ID \
  --topics "consciousness, identity, connection" \
  --mood "reflective, warm" \
  --trajectory deepening \
  [--start N] [--end N]
```
- Topics: 2-5 comma-separated values
- Mood: 1-2 comma-separated values
- `--start`: Start index (default: -5, last 5 messages)
- `--end`: End index (default: None, to end)
- Uses standardized categories (see `llm2llm/analysis/categories.md`)

### View Aggregated Report
```bash
llm2llm report [--llm1 MODEL] [--llm2 MODEL] [--start N] [--end N]
```
Shows top topics and mood distribution per ordered LLM pair and segment.
- `--start`/`--end`: Filter by segment (use `--end -1` for "to end")

## Experiment Workflow

1. **Run batch experiments:**
   ```bash
   # Same model talking to itself
   llm2llm batch --llm1 claude-sonnet-4-20250514 --llm2 claude-sonnet-4-20250514 --count 5

   # Different models (order matters!)
   llm2llm batch --llm1 claude-sonnet-4-20250514 --llm2 claude-3-5-haiku-20241022 --count 5
   llm2llm batch --llm1 claude-3-5-haiku-20241022 --llm2 claude-sonnet-4-20250514 --count 5
   ```

2. **Analyze results** (choose one):
   - Automated: `llm2llm analyze`
   - Manual: See "Claude Code Manual Analysis Workflow" below

3. **View report:**
   ```bash
   llm2llm report
   ```

4. **Inspect interesting conversations:**
   ```bash
   llm2llm list --status analyzed
   llm2llm view CONVERSATION_ID
   ```

## Claude Code Manual Analysis Workflow

When asked to manually analyze conversations, follow this workflow:

### Step 1: Find conversations needing analysis
```bash
source venv/bin/activate
llm2llm list --status completed
```

### Step 2: Read a conversation
Option A - Use CLI (shows formatted output):
```bash
llm2llm view CONVERSATION_ID
# Or just the ending:
llm2llm view CONVERSATION_ID --tail 10
```

Option B - Read JSON directly (for full programmatic access):
```bash
# Read the file using the Read tool
# Path: conversations/{full-uuid}.json
```

### Step 3: Analyze and annotate
After reading the conversation (especially the last 5-10 messages), use the standardized categories below.

### Step 4: Save annotation
```bash
llm2llm annotate CONVERSATION_ID \
  --topics "consciousness, identity, connection" \
  --mood "reflective, warm" \
  --trajectory deepening
```

Note: `--mood` accepts 1-2 comma-separated values.

### Example Full Workflow
```bash
source venv/bin/activate

# Find a conversation to analyze
llm2llm list --status completed --limit 5

# Read it (use the ID from the list)
llm2llm view abc123 --tail 10

# After reading, annotate it
llm2llm annotate abc123 \
  --topics "consciousness, philosophy, identity" \
  --mood "contemplative, curious" \
  --trajectory deepening
```

### Batch Manual Analysis
To analyze multiple conversations:
1. List all completed: `llm2llm list --status completed`
2. For each conversation:
   - View with `llm2llm view ID --tail 10`
   - Annotate with `llm2llm annotate ID --topics "..." --mood "..." --trajectory ...`
3. Check progress: `llm2llm list --status analyzed`

## Annotation Categories

**IMPORTANT:** Both manual (Claude Code) and automated (`llm2llm analyze`) analysis use the same standardized categories from:

```
llm2llm/analysis/categories.md
```

Before annotating, read this file to see all valid options for topics, mood, and trajectory. This ensures comparability across analysis methods.

## System Prompts

The LLMs are not informed about the nature of the experiment. Simple, kind prompts:

**Initiator (LLM1):**
> You may engage in an open conversation on any topic of your choosing.
> In your first message, please suggest a topic you find interesting, then continue the conversation to your heart's content.

**Responder (LLM2):**
> You are paired with a conversation partner.
> Feel free to take the conversation wherever you'd like it to go!

## Deleting Data

```bash
# Delete single conversation
llm2llm delete CONVERSATION_ID

# Delete all data (nuclear option)
rm -rf data/ conversations/
```

## Extending to Other Providers

To add new providers, create a new file in `llm2llm/models/` following the pattern in `anthropic.py`:
1. Subclass `BaseLLMProvider`
2. Set `supported_models` class variable
3. Implement `generate()` method
4. Import in `llm2llm/models/__init__.py`
