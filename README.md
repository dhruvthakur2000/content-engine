# AI Content Engine

> Turns your daily engineering notes and git commits into platform-ready LinkedIn posts, Twitter threads, and technical blog posts — using a 7-node LangGraph pipeline backed by Qwen2.5-72B on HuggingFace Inference.

---

## What This Does

You write raw notes at the end of a dev session:

```
Fixed websocket buffer flush threshold today.
Latency dropped from 820ms to 580ms.
VAD still triggering on background noise — not fixed yet.
```

The engine extracts the engineering story, picks a narrative angle, applies your writing style, and generates:

- A LinkedIn post with a scroll-stopping hook and your actual numbers
- A Twitter/X thread structured for developer engagement
- A full 1200–1500 word technical blog post (two-stage: blueprint → draft)

Built in public as a personal tool, designed to scale into a SaaS product.

---

## Architecture

```
Developer Notes + Git Log
         │
         ▼
  run_pipeline_service()
    │
    ├── Memory Search (ChromaDB — finds similar past content)
    │
    ▼
LangGraph Pipeline (7 nodes)
    │
    ├── parse_notes      ──→ Cache Layer (SHA-256 hash lookup)
    ├── parse_git        ──→ Cache Layer
    ├── context_builder  (pure transform, no LLM)
    ├── angle_generator  ──→ Cache Layer
    ├── style_selector   (loads creator style profile, ~1ms)
    ├── blog_blueprint   (stage 1 of 2-stage blog, LLM)
    └── post_generator   (LinkedIn + Twitter + Blog, separate LLM call per platform)
         │
         ▼
    Memory Store (saves run for future similarity search)
         │
         ▼
    generated_posts → FastAPI → Streamlit UI
```

**Stack:** Python 3.10+ · FastAPI · LangGraph · LangChain · Qwen2.5-72B · HuggingFace Inference Router · ChromaDB · Streamlit · Pydantic-Settings · structlog · uv

---

## Features

### 7-Node LangGraph Pipeline
A deterministic directed graph where each node has a single responsibility. Nodes communicate through a typed `PipelineState` TypedDict — no globals, no side effects. Errors in one node don't kill the pipeline.

### Qwen2.5-72B via HuggingFace Inference Router
The LLM backend uses HuggingFace's OpenAI-compatible router (`router.huggingface.co/v1`). Swap inference providers without touching code — append `:sambanova`, `:together`, or `:nebius` to the model name in `.env`.

### Platform Psychology Prompts
LinkedIn and Twitter have different audiences making different content decisions. The prompt system encodes this explicitly: LinkedIn gets a storytelling-first prompt with audience psychology context; Twitter gets a punchy, hook-first thread structure. Same engineering input produces platform-native output for each.

### Creator Style Profiles
Four profiles ship out of the box (`dhruv_default`, `swyx`, `primagen`, `levelsio`). Each `.md` file describes hook patterns, sentence rhythm, tone rules, and structural patterns. The style loader injects these into every generation prompt. Add your own by creating `creator_styles/yourname.md` — no code changes.

### Two-Stage Blog Generation
Single-call blog generation produces flat summaries. This pipeline splits it:
- **Stage 1** (`blog_blueprint_node`): LLM plans title options, section structure, hook paragraph, key technical points, what to avoid.
- **Stage 2** (`post_generator`): LLM writes 1200–1500 words against the blueprint.

Users can paste extra material (YouTube transcripts, reference blog links, docs) to enrich the blog source material.

### Deterministic Cache Layer
SHA-256 content-addressable cache for `parse_notes`, `parse_git`, and `angle_generator` nodes. Same input = same hash = instant return from JSON file. Configurable TTL (default 24h). Every API response includes `cache_hits` in metadata showing exactly which nodes were served from cache vs live LLM calls. Expected reduction: 40–70% in cost and latency for repeated or similar inputs.

### Semantic Memory Layer (ChromaDB)
Stores generated posts as embeddings in a local ChromaDB vector database. Before each pipeline run, searches for semantically similar past content. If a match exceeds the configurable similarity threshold (default: 0.82), the past posts are injected into the generation prompt as a style reference — not to copy, but to calibrate tone and structure. Memory search happens outside the pipeline so failures are invisible to the user.

### Centralized Configuration
Every configurable value — API keys, model ID, inference provider, temperature, max tokens, cache TTL, memory threshold, ports, CORS — lives in `settings.py` as a typed Pydantic field. No hardcoded values anywhere in the codebase. Environment: `.env` file in development, system environment variables in production via systemd.

### Structured Logging
`structlog` writes JSON-formatted logs to both terminal and file. Every node logs `node_started` and `node_completed` events with timing in milliseconds. Production logs are queryable and machine-parseable.

---

## Project Structure

```
content_engine/
├── backend/
│   ├── api/
│   │   └── main.py              # FastAPI app — 7 endpoints
│   ├── cache/
│   │   └── cache_manager.py     # SHA-256 hash cache, TTL, stats
│   ├── config/
│   │   └── settings.py          # All config — Pydantic-Settings
│   ├── ingestion/
│   │   ├── dump_parser.py       # Notes file reader + cleaner
│   │   └── git_parser.py        # GitPython commit history reader
│   ├── llm/
│   │   ├── prompts.py           # All prompt templates
│   │   ├── providers.py         # LLM abstraction — HuggingFaceProvider
│   │   └── style_loader.py      # Creator style profile loader
│   ├── memory/
│   │   └── content_memory.py    # ChromaDB semantic memory layer
│   ├── services/
│   │   └── run_pipeline.py      # Orchestration — memory search + graph invoke
│   └── utils/
│       └── logger.py            # structlog JSON logger
├── creator_styles/
│   ├── dhruv_default.md         # Personal style profile
│   ├── swyx.md
│   ├── primagen.md
│   └── levelsio.md
├── frontend/
│   └── streamlit_app.py         # 3-page UI: Generate, Blog Studio, Settings
├── inputs/
│   └── today_dump.txt           # Drop your daily notes here
├── pipeline/
│   ├── graph.py                 # LangGraph StateGraph assembly
│   ├── state.py                 # PipelineState TypedDict
│   └── nodes/
│       ├── parse_notes.py       # Stage 1: LLM extracts from notes
│       ├── parse_git.py         # Stage 2: LLM extracts from commits
│       ├── context_builder.py   # Stage 3: Pure merge, no LLM
│       ├── angle.py             # Stage 4: Narrative angle selection
│       ├── style_selector.py    # Stage 5: Load creator style
│       ├── blog_blueprint.py    # Stage 6: Blog structure plan
│       └── post_generator.py    # Stage 7: Platform content generation
├── pyproject.toml
├── setup.sh
├── start.sh
└── .env.example
```

---

## Setup

### Requirements

- Python 3.10+
- Git
- A HuggingFace account (free)

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/content-engine.git
cd content-engine
chmod +x setup.sh start.sh
./setup.sh
```

### 2. Get your HuggingFace token

1. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Create a **Fine-grained** token
3. Enable permission: **Make calls to Inference Providers**
4. Copy the token (starts with `hf_...`)

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:
```
HF_TOKEN=hf_your_token_here
```

Optional — pin to a specific inference provider for consistent latency:
```
LLM_MODEL=Qwen/Qwen2.5-72B-Instruct:sambanova
```

### 4. Run

```bash
./start.sh
```

- Streamlit UI: [http://localhost:8501](http://localhost:8501)
- API docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)

### Enable semantic memory (optional)

```bash
source .venv/bin/activate
uv pip install chromadb
```

Then in `.env`:
```
MEMORY_ENABLED=true
```

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/generate` | Generate content from raw notes + git |
| `POST` | `/generate/file` | Generate from server-side notes file |
| `GET` | `/health` | Health check including cache + memory stats |
| `GET` | `/styles` | List available creator style profiles |
| `GET` | `/models` | List available LLM models |
| `GET` | `/cache/stats` | Cache file count, size, TTL info |
| `POST` | `/cache/clear` | Delete cache files (all or older than N hours) |
| `GET` | `/memory/stats` | ChromaDB entry count and similarity threshold |

### Example request

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "raw_notes": "Fixed websocket buffer today. Latency 820ms → 580ms. Buffer flush threshold was 4KB, changed to 1KB.",
    "platforms": ["linkedin", "twitter"],
    "style": "dhruv_default"
  }'
```

### Example response

```json
{
  "success": true,
  "generated_posts": {
    "linkedin": "820ms → 580ms.\n\nThat was the latency drop after one config change...",
    "twitter": "1/ My voice pipeline had 820ms latency.\n\nThe model wasn't slow..."
  },
  "metadata": {
    "model": "Qwen/Qwen2.5-72B-Instruct",
    "cache_hits": ["parse_notes", "parse_git"],
    "cached_node_count": 2,
    "memory_hit": false,
    "narrative_angle": "PERFORMANCE_BREAKTHROUGH",
    "style_used": "dhruv_default",
    "total_service_duration_ms": 8240
  }
}
```

---

## Configuration Reference

All settings are environment variables, documented in `.env.example`.

| Variable | Default | Description |
|----------|---------|-------------|
| `HF_TOKEN` | required | HuggingFace access token |
| `LLM_MODEL` | `Qwen/Qwen2.5-72B-Instruct` | Model ID, optionally with `:provider` |
| `HF_BASE_URL` | `https://router.huggingface.co/v1` | Inference router endpoint |
| `LLM_TEMPERATURE` | `0.7` | Generation randomness (0.0–2.0) |
| `LLM_MAX_TOKENS` | `2500` | Max tokens per response |
| `LLM_REQUEST_TIMEOUT` | `120` | API timeout in seconds |
| `CACHE_ENABLED` | `true` | Enable deterministic cache |
| `CACHE_DIR` | `cache` | Cache file directory |
| `CACHE_TTL_HOURS` | `24` | Cache entry lifetime in hours |
| `MEMORY_ENABLED` | `false` | Enable ChromaDB semantic memory |
| `MEMORY_DIR` | `memory` | ChromaDB storage directory |
| `MEMORY_SIMILARITY_THRESHOLD` | `0.82` | Minimum similarity for memory match |
| `APP_ENV` | `development` | `development` or `production` |
| `API_PORT` | `8000` | FastAPI port |
| `STREAMLIT_PORT` | `8501` | Streamlit port |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Adding a Creator Style

Create `creator_styles/yourname.md` following this structure:

```markdown
# Your Name — Creator Style Profile

## Voice
[Describe overall tone and approach]

## Hook Patterns
- "Pattern 1"
- "Pattern 2"

## Sentence Rhythm
[Short? Long? Mixed? Describe the cadence]

## Structure Pattern
[Hook → Context → Insight → Detail → Lesson]

## Tone Rules
- What to always do
- What to never say

## Technical Density
[Low / Medium / High — and why]
```

Pass `style=yourname` in any API request. No code changes needed.

---

## Design Decisions

**Why LangGraph instead of a simple function chain?**
Each node is independently testable, replaceable, and observable. The `PipelineState` TypedDict makes data flow explicit — you can inspect what any node received and what it returned. Adding a new node means adding one function and two lines in `graph.py`.

**Why separate LLM calls per platform instead of one combined call?**
A single call producing LinkedIn + Twitter + Blog in one response produces noticeably worse quality. Each platform has different length constraints, different audience psychology, and different structural requirements. Separate calls let each prompt be fully optimized for its target.

**Why SHA-256 for the cache key?**
Content-addressable caching: same input always maps to the same key, different input always maps to a different key. No collision risk in practice. The hash is computed in microseconds — negligible overhead before a 10-second LLM call.

**Why is memory search outside the LangGraph pipeline?**
Memory is advisory. If the search fails (ChromaDB unavailable, import error), the pipeline should continue normally with zero user-visible impact. Wrapping it in the service layer with a broad `try/except` achieves this. Inside a pipeline node, an exception would stall the graph.

**Why `total=False` in `PipelineState`?**
With `total=False`, all TypedDict fields are optional. This lets nodes return only the fields they're responsible for — LangGraph merges partial dicts into the shared state. Without it, every node would need to return all fields.

---

## Roadmap

- [ ] Trend analyzer node — scrapes top-performing dev posts, injects current topic patterns
- [ ] Style learning from examples — paste 5 posts, generate a custom style profile
- [ ] Async pipeline execution — parallel node execution for platforms that don't depend on each other
- [ ] Web UI cache management panel in Streamlit settings page
- [ ] Post scheduling integration (LinkedIn API, Buffer)
- [ ] Multi-day digest mode — generate weekly retrospective from 5 days of notes

---

## License

MIT
