# ============================================================
# frontend/streamlit_app.py  [REDESIGNED — Professional UI]
#
# AESTHETIC: Dark terminal / developer tool
#   - Deep charcoal background (#0d0f14)
#   - Amber accent (#f59e0b) — like a terminal cursor
#   - JetBrains Mono for headings, Inter for body
#   - Card-based layout with subtle borders
#   - Clean, dense, information-rich
#
# PAGES:
#   1. ⚡ Generate      — main content generation
#   2. 📝 Blog Studio   — two-stage blog generation
#   3. 📊 Dashboard     — cache + memory stats, pipeline health
#   4. ⚙️  Settings     — config, styles, models
# ============================================================

import requests
import time
from datetime import datetime
import streamlit as st

# ── Page config — must be first Streamlit call ────────────────
st.set_page_config(
    page_title="Content Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ─────────────────────────────────────────────────
DEFAULT_API_URL = "http://localhost:8000"

EXAMPLE_NOTES = """Worked on the voice pipeline today.

Tracked down the latency issue — finally.
Websocket buffer was holding chunks too long before forwarding.
Changed the flush threshold from 4KB to 1KB.
Latency dropped: 820ms → 580ms.

Also: VAD is still triggering on background noise (AC unit).
Haven't fixed yet but I know the cause.
Tried adjusting sensitivity — marginal improvement only.

Next: noise floor detection, maybe a simple energy baseline approach."""

EXAMPLE_GIT = """fix: websocket buffer flush threshold too high
feat: add per-session redis state persistence
refactor: extract vad config to separate module
fix: race condition in audio chunk processing"""

STYLE_META = {
    "dhruv_default": {
        "label": "Dhruv (Default)",
        "desc": "Honest about struggles. Specific. Build-in-public voice.",
        "icon": "🔥",
    },
    "swyx": {
        "label": "swyx",
        "desc": "Reflective. Connects engineering to bigger patterns.",
        "icon": "🧠",
    },
    "primagen": {
        "label": "ThePrimeagen",
        "desc": "High energy. Direct. Opinionated. Zero fluff.",
        "icon": "⚡",
    },
    "levelsio": {
        "label": "levels.io",
        "desc": "Numbers-first. Radical transparency. Ship-focused.",
        "icon": "📊",
    },
}

PLATFORM_LIMITS = {
    "linkedin": {"max": 3000, "ideal": 1300, "unit": "chars"},
    "twitter": {"max": 1400, "ideal": 700, "unit": "chars"},
    "blog": {"max": 99999, "ideal": 7500, "unit": "chars"},
}

# ── CSS — Dark terminal aesthetic ─────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

/* ── Root variables ── */
:root {
    --bg:        #0d0f14;
    --bg-card:   #13161e;
    --bg-input:  #1a1d26;
    --border:    #252836;
    --border-hi: #2e3347;
    --amber:     #f59e0b;
    --amber-dim: #92610a;
    --green:     #10b981;
    --red:       #ef4444;
    --blue:      #3b82f6;
    --text:      #e2e8f0;
    --text-dim:  #64748b;
    --text-mid:  #94a3b8;
    --mono:      'JetBrains Mono', monospace;
    --sans:      'Inter', sans-serif;
}

/* ── Global overrides ── */
.stApp {
    background-color: var(--bg) !important;
    font-family: var(--sans) !important;
    color: var(--text) !important;
}

/* Hide Streamlit branding */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem !important; max-width: 1400px; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: var(--bg-card) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span { color: var(--text-mid) !important; font-family: var(--sans) !important; }

/* ── Typography ── */
h1 { font-family: var(--mono) !important; font-size: 1.5rem !important; font-weight: 700 !important; color: var(--amber) !important; letter-spacing: -0.02em; margin-bottom: 0.25rem !important; }
h2 { font-family: var(--mono) !important; font-size: 1.1rem !important; font-weight: 600 !important; color: var(--text) !important; letter-spacing: -0.01em; }
h3 { font-family: var(--mono) !important; font-size: 0.95rem !important; font-weight: 600 !important; color: var(--text-mid) !important; }
p, li { font-family: var(--sans) !important; color: var(--text-mid) !important; font-size: 0.9rem !important; }

/* ── Inputs ── */
.stTextArea textarea, .stTextInput input {
    background-color: var(--bg-input) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: 0.82rem !important;
    caret-color: var(--amber) !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--amber) !important;
    box-shadow: 0 0 0 2px rgba(245,158,11,0.15) !important;
}
label { color: var(--text-mid) !important; font-size: 0.8rem !important; font-family: var(--sans) !important; font-weight: 500 !important; letter-spacing: 0.04em !important; text-transform: uppercase !important; }

/* ── Buttons ── */
.stButton > button {
    background: var(--amber) !important;
    color: #0d0f14 !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: var(--mono) !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.02em !important;
    padding: 0.5rem 1.2rem !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover { background: #d97706 !important; transform: translateY(-1px); box-shadow: 0 4px 16px rgba(245,158,11,0.3) !important; }
.stButton > button:disabled { background: var(--bg-input) !important; color: var(--text-dim) !important; }

/* ── Secondary button style (for copy etc.) ── */
.stDownloadButton > button {
    background: transparent !important;
    color: var(--amber) !important;
    border: 1px solid var(--amber-dim) !important;
    border-radius: 6px !important;
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
}
.stDownloadButton > button:hover { background: rgba(245,158,11,0.08) !important; border-color: var(--amber) !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { background: var(--bg-card) !important; border-radius: 8px !important; padding: 4px !important; border: 1px solid var(--border) !important; gap: 2px; }
.stTabs [data-baseweb="tab"] { font-family: var(--mono) !important; font-size: 0.82rem !important; color: var(--text-dim) !important; border-radius: 5px !important; padding: 6px 16px !important; }
.stTabs [aria-selected="true"] { background: var(--amber) !important; color: #0d0f14 !important; font-weight: 700 !important; }

/* ── Metrics ── */
[data-testid="metric-container"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 0.75rem 1rem !important;
}
[data-testid="metric-container"] label { color: var(--text-dim) !important; font-size: 0.72rem !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: var(--amber) !important; font-family: var(--mono) !important; font-size: 1.1rem !important; font-weight: 700 !important; }

/* ── Select boxes + radio ── */
.stSelectbox > div > div {
    background: var(--bg-input) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: 0.85rem !important;
}
.stRadio label span { color: var(--text-mid) !important; font-size: 0.85rem !important; }

/* ── Checkboxes ── */
.stCheckbox label span { color: var(--text) !important; font-family: var(--sans) !important; font-size: 0.88rem !important; }

/* ── Divider ── */
hr { border-color: var(--border) !important; margin: 1rem 0 !important; }

/* ── Alerts ── */
.stSuccess { background: rgba(16,185,129,0.1) !important; border: 1px solid rgba(16,185,129,0.3) !important; color: #10b981 !important; border-radius: 6px !important; }
.stError   { background: rgba(239,68,68,0.1) !important; border: 1px solid rgba(239,68,68,0.3) !important; color: #ef4444 !important; border-radius: 6px !important; }
.stWarning { background: rgba(245,158,11,0.1) !important; border: 1px solid rgba(245,158,11,0.3) !important; color: #f59e0b !important; border-radius: 6px !important; }
.stInfo    { background: rgba(59,130,246,0.1) !important; border: 1px solid rgba(59,130,246,0.3) !important; color: #93c5fd !important; border-radius: 6px !important; }
.stSuccess p, .stError p, .stWarning p, .stInfo p { color: inherit !important; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: var(--amber) !important; }

/* ── Code blocks ── */
code { background: var(--bg-input) !important; color: var(--amber) !important; font-family: var(--mono) !important; padding: 2px 6px !important; border-radius: 4px !important; font-size: 0.82rem !important; }
pre { background: var(--bg-input) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; }

/* ── Custom card components ── */
.ce-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}
.ce-card-accent {
    border-left: 3px solid var(--amber);
}
.ce-badge {
    display: inline-block;
    background: rgba(245,158,11,0.12);
    border: 1px solid rgba(245,158,11,0.3);
    color: var(--amber);
    font-family: var(--mono);
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.ce-badge-green {
    background: rgba(16,185,129,0.12);
    border-color: rgba(16,185,129,0.3);
    color: var(--green);
}
.ce-badge-red {
    background: rgba(239,68,68,0.12);
    border-color: rgba(239,68,68,0.3);
    color: var(--red);
}
.ce-badge-blue {
    background: rgba(59,130,246,0.12);
    border-color: rgba(59,130,246,0.3);
    color: var(--blue);
}
.ce-label {
    font-family: var(--mono);
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 0.4rem;
}
.ce-stat-row {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    margin: 0.5rem 0;
}
.ce-stat {
    display: flex;
    flex-direction: column;
    gap: 2px;
}
.ce-stat-val {
    font-family: var(--mono);
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--amber);
}
.ce-stat-label {
    font-size: 0.72rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.ce-char-bar-wrap {
    height: 4px;
    background: var(--bg-input);
    border-radius: 2px;
    margin: 4px 0 2px;
    overflow: hidden;
}
.ce-char-bar {
    height: 100%;
    border-radius: 2px;
    transition: width 0.3s ease;
}
.sidebar-logo {
    font-family: var(--mono);
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--amber);
    letter-spacing: -0.02em;
    line-height: 1;
}
.sidebar-sub {
    font-family: var(--sans);
    font-size: 0.78rem;
    color: var(--text-dim);
    margin-top: 2px;
}
.api-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
}
.api-dot-green { background: var(--green); box-shadow: 0 0 6px var(--green); }
.api-dot-red   { background: var(--red); }
.pipeline-step {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 0;
    border-bottom: 1px solid var(--border);
    font-family: var(--mono);
    font-size: 0.8rem;
    color: var(--text-mid);
}
.pipeline-step:last-child { border-bottom: none; }
.step-num {
    width: 22px; height: 22px;
    border-radius: 50%;
    background: var(--bg-input);
    border: 1px solid var(--border-hi);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.68rem; font-weight: 700; color: var(--text-dim);
    flex-shrink: 0;
}
.platform-toggle {
    display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────────────────────

def api_get(path: str, timeout: int = 5):
    api_url = st.session_state.get("api_url", DEFAULT_API_URL)
    try:
        r = requests.get(f"{api_url}{path}", timeout=timeout)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def api_post(path: str, payload: dict, timeout: int = 150):
    api_url = st.session_state.get("api_url", DEFAULT_API_URL)
    try:
        r = requests.post(f"{api_url}{path}", json=payload, timeout=timeout)
        return r.json(), r.status_code
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to API. Is it running?"}, 503
    except requests.exceptions.Timeout:
        return {"error": f"Request timed out after {timeout}s."}, 408
    except Exception as e:
        return {"error": str(e)}, 500


def char_bar_html(count: int, ideal: int, max_val: int, platform: str) -> str:
    pct = min(100, (count / max_val) * 100) if max_val else 0
    if count <= ideal:
        color = "#10b981"
    elif count <= max_val * 0.85:
        color = "#f59e0b"
    else:
        color = "#ef4444"
    label = f"{count:,} / {ideal:,} ideal"
    return f"""
    <div class='ce-char-bar-wrap'>
        <div class='ce-char-bar' style='width:{pct:.0f}%;background:{color}'></div>
    </div>
    <span style='font-size:0.72rem;color:{color};font-family:var(--mono)'>{label}</span>
    """


def badge(text: str, variant: str = "") -> str:
    cls = f"ce-badge ce-badge-{variant}" if variant else "ce-badge"
    return f"<span class='{cls}'>{text}</span>"


def check_api_health() -> dict | None:
    return api_get("/health", timeout=4)


# ── Session state defaults ─────────────────────────────────────
for key, val in {
    "api_url": DEFAULT_API_URL,
    "author_name": "Dhruv",
    "last_result": None,
    "last_posts": {},
    "blog_result": "",
    "blog_meta": {},
    "api_status": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:

    st.markdown("""
    <div class='sidebar-logo'>⚡ Content Engine</div>
    <div class='sidebar-sub'>Notes → Posts. Automatically.</div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # API status indicator
    health = check_api_health()
    if health:
        status_html = "<span class='api-dot api-dot-green'></span><span style='font-size:0.8rem;color:#10b981;font-family:var(--mono)'>API Online</span>"
        model_short = health.get("checks", {}).get("model", "—").split("/")[-1][:20]
    else:
        status_html = "<span class='api-dot api-dot-red'></span><span style='font-size:0.8rem;color:#ef4444;font-family:var(--mono)'>API Offline</span>"
        model_short = "—"

    st.markdown(status_html, unsafe_allow_html=True)
    st.markdown(f"<span style='font-size:0.72rem;color:var(--text-dim);font-family:var(--mono)'>{model_short}</span>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Navigation
    page = st.radio(
        "nav",
        ["⚡  Generate", "📝  Blog Studio", "📊  Dashboard", "⚙️  Settings"],
        label_visibility="collapsed",
    )

    st.markdown("<hr>", unsafe_allow_html=True)

    # Author
    st.session_state.author_name = st.text_input(
        "Author Name",
        value=st.session_state.author_name,
        placeholder="Your name",
    )

    # Style selector
    styles_data = api_get("/styles") or {}
    available_styles = styles_data.get("available_styles", list(STYLE_META.keys()))

    selected_style = st.selectbox(
        "Writing Style",
        options=available_styles,
        index=0,
    )

    meta = STYLE_META.get(selected_style, {})
    if meta:
        st.markdown(f"""
        <div class='ce-card ce-card-accent' style='padding:0.75rem 1rem;margin-top:0.5rem'>
            <div style='font-size:1.1rem;margin-bottom:3px'>{meta.get('icon','')}</div>
            <div style='font-family:var(--mono);font-size:0.8rem;color:var(--amber);font-weight:600'>{meta.get('label','')}</div>
            <div style='font-size:0.75rem;color:var(--text-dim);margin-top:3px'>{meta.get('desc','')}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    st.session_state.api_url = st.text_input(
        "API Endpoint",
        value=st.session_state.api_url,
    )


# ══════════════════════════════════════════════════════════════
# PAGE 1 — GENERATE
# ══════════════════════════════════════════════════════════════
if "Generate" in page:

    # Page header
    st.markdown(f"""
    <div style='margin-bottom:1.5rem'>
        <h1>⚡ Generate</h1>
        <div style='font-family:var(--sans);font-size:0.85rem;color:var(--text-dim)'>
            Writing as <span style='color:var(--amber);font-family:var(--mono)'>{st.session_state.author_name}</span>
            &nbsp;·&nbsp;
            Style: <span style='color:var(--amber);font-family:var(--mono)'>{selected_style}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    left, right = st.columns([1, 1], gap="large")

    with left:

        # Notes input
        st.markdown("<div class='ce-label'>Engineering Notes</div>", unsafe_allow_html=True)
        raw_notes = st.text_area(
            "notes_input",
            value=EXAMPLE_NOTES,
            height=220,
            label_visibility="collapsed",
            placeholder="Brain dump what you built, fixed, or learned today.",
        )
        note_chars = len(raw_notes)
        st.markdown(f"<span style='font-family:var(--mono);font-size:0.72rem;color:var(--text-dim)'>{note_chars:,} chars</span>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Git log
        st.markdown("<div class='ce-label'>Git Log <span style='color:var(--text-dim);font-weight:400;text-transform:none'>(optional)</span></div>", unsafe_allow_html=True)
        raw_git = st.text_area(
            "git_input",
            value=EXAMPLE_GIT,
            height=90,
            label_visibility="collapsed",
            placeholder="Paste: git log --oneline -20",
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Platform selection
        st.markdown("<div class='ce-label'>Platforms</div>", unsafe_allow_html=True)
        pc1, pc2, pc3 = st.columns(3)
        gen_li = pc1.checkbox("LinkedIn", value=True)
        gen_tw = pc2.checkbox("Twitter/X", value=True)
        gen_bl = pc3.checkbox("Blog", value=False)

        platforms = []
        if gen_li: platforms.append("linkedin")
        if gen_tw: platforms.append("twitter")
        if gen_bl: platforms.append("blog")

        st.markdown("<br>", unsafe_allow_html=True)

        if not platforms:
            st.warning("Select at least one platform.")

        # Generate button
        generate_clicked = st.button(
            "⚡  Run Pipeline",
            type="primary",
            disabled=not platforms or not raw_notes.strip(),
            use_container_width=True,
        )

        # Pipeline steps preview
        st.markdown("""
        <div class='ce-card' style='margin-top:1rem;padding:1rem 1.25rem'>
            <div class='ce-label' style='margin-bottom:0.5rem'>Pipeline</div>
            <div class='pipeline-step'><div class='step-num'>1</div>parse_notes</div>
            <div class='pipeline-step'><div class='step-num'>2</div>parse_git</div>
            <div class='pipeline-step'><div class='step-num'>3</div>context_builder</div>
            <div class='pipeline-step'><div class='step-num'>4</div>angle_generator</div>
            <div class='pipeline-step'><div class='step-num'>5</div>style_selector</div>
            <div class='pipeline-step'><div class='step-num'>6</div>blog_blueprint</div>
            <div class='pipeline-step'><div class='step-num'>7</div>post_generator</div>
        </div>
        """, unsafe_allow_html=True)

    with right:

        st.markdown("<div class='ce-label'>Output</div>", unsafe_allow_html=True)

        # Execute generation
        if generate_clicked and platforms:
            progress_msgs = [
                "Parsing engineering notes...",
                "Analyzing git history...",
                "Building context...",
                "Selecting narrative angle...",
                "Loading style profile...",
                "Generating content...",
            ]
            with st.spinner("Pipeline running..."):
                payload = {
                    "raw_notes": raw_notes,
                    "raw_git_log": raw_git,
                    "platforms": platforms,
                    "author_name": st.session_state.author_name,
                    "style": selected_style,
                    "extra_material": "",
                }
                result, status = api_post("/generate", payload, timeout=150)

            if status == 200 and result.get("success"):
                st.session_state["last_result"] = result
                st.session_state["last_posts"] = result.get("generated_posts", {})
                st.success("Generation complete.")
            else:
                err = result.get("detail") or result.get("error") or "Unknown error"
                st.error(f"{err}")

        # Render results
        posts = st.session_state.get("last_posts", {})
        meta = st.session_state.get("last_result") or {}
        meta_data = meta.get("metadata", {}) if isinstance(meta, dict) else {}

        if posts:
            # Metadata strip
            total_s = meta_data.get("total_service_duration_ms", 0) // 1000
            angle = meta_data.get("narrative_angle", "—").replace("_", " ")
            cached = meta_data.get("cached_node_count", 0)
            mem_hit = meta_data.get("memory_hit", False)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("⏱ Time", f"{total_s}s")
            m2.metric("📐 Angle", angle[:18])
            m3.metric("💾 Cached", f"{cached}/3 nodes")
            m4.metric("🧠 Memory", "Hit" if mem_hit else "Miss")

            st.markdown("<hr>", unsafe_allow_html=True)

            tabs = st.tabs([f"  {p.capitalize()}  " for p in posts])
            for tab, (platform, content) in zip(tabs, posts.items()):
                with tab:
                    if content.startswith("["):
                        st.error(content)
                        continue

                    st.text_area(
                        f"out_{platform}",
                        value=content,
                        height=380,
                        label_visibility="collapsed",
                    )

                    # Char bar
                    lim = PLATFORM_LIMITS.get(platform, {"ideal": 1000, "max": 5000})
                    st.markdown(
                        char_bar_html(len(content), lim["ideal"], lim["max"], platform),
                        unsafe_allow_html=True,
                    )

                    st.download_button(
                        "↓ Download",
                        data=content,
                        file_name=f"{platform}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                        mime="text/plain",
                        key=f"dl_{platform}_{int(time.time())}",
                    )

        elif not generate_clicked:
            st.markdown("""
            <div class='ce-card' style='margin-top:2rem;text-align:center;padding:3rem 1.5rem'>
                <div style='font-size:2.5rem;margin-bottom:1rem'>⚡</div>
                <div style='font-family:var(--mono);color:var(--amber);font-size:0.9rem;margin-bottom:0.5rem'>Ready</div>
                <div style='font-size:0.82rem;color:var(--text-dim)'>Fill in your notes and hit Run Pipeline.</div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# PAGE 2 — BLOG STUDIO
# ══════════════════════════════════════════════════════════════
elif "Blog Studio" in page:

    st.markdown("""
    <div style='margin-bottom:1.5rem'>
        <h1>📝 Blog Studio</h1>
        <div style='font-size:0.85rem;color:var(--text-dim)'>
            Two-stage generation: <span style='color:var(--amber);font-family:var(--mono)'>blueprint</span>
            → <span style='color:var(--amber);font-family:var(--mono)'>1200–1500 word post</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    bl, br = st.columns([1, 1], gap="large")

    with bl:

        st.markdown("<div class='ce-label'>Engineering Notes</div>", unsafe_allow_html=True)
        blog_notes = st.text_area(
            "blog_notes",
            value=EXAMPLE_NOTES,
            height=180,
            label_visibility="collapsed",
        )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
        <div class='ce-label'>Extra Reference Material
            <span style='font-family:var(--sans);text-transform:none;letter-spacing:0;font-weight:400;color:var(--text-dim)'> — optional</span>
        </div>
        <div style='font-size:0.78rem;color:var(--text-dim);margin-bottom:0.4rem'>
            Paste blog links, YouTube transcripts, reference docs. Enriches the post significantly.
        </div>
        """, unsafe_allow_html=True)
        extra_material = st.text_area(
            "extra",
            height=130,
            label_visibility="collapsed",
            placeholder="--- Blog reference ---\nPaste key paragraphs here\n\n--- YouTube transcript ---\n...",
        )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("<div class='ce-label'>Git Log <span style='color:var(--text-dim);font-weight:400;text-transform:none'>(optional)</span></div>", unsafe_allow_html=True)
        blog_git = st.text_area(
            "blog_git",
            value=EXAMPLE_GIT,
            height=80,
            label_visibility="collapsed",
        )

        st.markdown("<br>", unsafe_allow_html=True)

        blog_clicked = st.button(
            "📝  Generate Blog Post",
            type="primary",
            use_container_width=True,
            disabled=not blog_notes.strip(),
        )

        st.markdown("""
        <div class='ce-card' style='margin-top:1rem'>
            <div class='ce-label' style='margin-bottom:0.5rem'>Two-Stage Process</div>
            <div class='pipeline-step'><div class='step-num'>1</div>LLM plans title, sections, hook paragraph</div>
            <div class='pipeline-step'><div class='step-num'>2</div>LLM writes 1200–1500 words against plan</div>
        </div>
        """, unsafe_allow_html=True)

    with br:

        st.markdown("<div class='ce-label'>Blog Output</div>", unsafe_allow_html=True)

        if blog_clicked:
            with st.spinner("Stage 1: Planning... → Stage 2: Writing..."):
                payload = {
                    "raw_notes": blog_notes,
                    "raw_git_log": blog_git,
                    "platforms": ["blog"],
                    "author_name": st.session_state.author_name,
                    "style": selected_style,
                    "extra_material": extra_material,
                }
                result, status = api_post("/generate", payload, timeout=200)

            if status == 200 and result.get("success"):
                content = result.get("generated_posts", {}).get("blog", "")
                st.session_state["blog_result"] = content
                st.session_state["blog_meta"] = result.get("metadata", {})
                st.success("Blog post generated.")
            else:
                err = result.get("detail") or result.get("error") or "Unknown error"
                st.error(f"{err}")

        blog_content = st.session_state.get("blog_result", "")
        blog_meta = st.session_state.get("blog_meta", {})

        if blog_content:
            word_count = len(blog_content.split())
            total_s = blog_meta.get("total_service_duration_ms", 0) // 1000
            two_stage = blog_meta.get("two_stage_blog", False)

            m1, m2, m3 = st.columns(3)
            m1.metric("⏱ Time", f"{total_s}s")
            m2.metric("📄 Words", f"~{word_count:,}")
            m3.metric("🔁 2-Stage", "Yes" if two_stage else "No")

            st.markdown("<hr>", unsafe_allow_html=True)

            view = st.radio(
                "View mode",
                ["📖 Rendered", "📝 Markdown"],
                horizontal=True,
                label_visibility="collapsed",
            )

            if "Rendered" in view:
                with st.container():
                    st.markdown(
                        f"<div class='ce-card' style='max-height:600px;overflow-y:auto'>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(blog_content)
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.text_area(
                    "blog_raw",
                    value=blog_content,
                    height=550,
                    label_visibility="collapsed",
                )

            st.download_button(
                "↓ Download .md",
                data=blog_content,
                file_name=f"blog_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown",
            )

        elif not blog_clicked:
            st.markdown("""
            <div class='ce-card' style='margin-top:2rem;text-align:center;padding:3rem 1.5rem'>
                <div style='font-size:2.5rem;margin-bottom:1rem'>📝</div>
                <div style='font-family:var(--mono);color:var(--amber);font-size:0.9rem;margin-bottom:0.5rem'>Blog Studio</div>
                <div style='font-size:0.82rem;color:var(--text-dim)'>Add notes and optional reference material, then generate.</div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# PAGE 3 — DASHBOARD
# ══════════════════════════════════════════════════════════════
elif "Dashboard" in page:

    st.markdown("""
    <div style='margin-bottom:1.5rem'>
        <h1>📊 Dashboard</h1>
        <div style='font-size:0.85rem;color:var(--text-dim)'>Cache stats · Memory stats · API health</div>
    </div>
    """, unsafe_allow_html=True)

    health = api_get("/health", timeout=5)
    cache_stats = api_get("/cache/stats")
    memory_stats = api_get("/memory/stats")

    # ── API Status ────────────────────────────────────────────
    st.markdown("<div class='ce-label'>API Status</div>", unsafe_allow_html=True)

    if health:
        status_val = health.get("status", "unknown")
        color = "#10b981" if status_val == "healthy" else "#f59e0b"
        model = health.get("checks", {}).get("model", "—")
        version = health.get("version", "—")
        token_ok = health.get("checks", {}).get("hf_token_configured", False)

        st.markdown(f"""
        <div class='ce-card ce-card-accent'>
            <div class='ce-stat-row'>
                <div class='ce-stat'>
                    <div class='ce-stat-val' style='color:{color}'>{status_val.upper()}</div>
                    <div class='ce-stat-label'>Status</div>
                </div>
                <div class='ce-stat'>
                    <div class='ce-stat-val' style='font-size:0.85rem'>{model.split("/")[-1]}</div>
                    <div class='ce-stat-label'>Model</div>
                </div>
                <div class='ce-stat'>
                    <div class='ce-stat-val' style='font-size:0.85rem'>v{version}</div>
                    <div class='ce-stat-label'>Version</div>
                </div>
                <div class='ce-stat'>
                    <div class='ce-stat-val' style='color:{"#10b981" if token_ok else "#ef4444"};font-size:0.85rem'>{"✓ Set" if token_ok else "✗ Missing"}</div>
                    <div class='ce-stat-label'>HF Token</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Styles
        styles = health.get("checks", {}).get("styles_available", [])
        if styles:
            st.markdown(
                "<div class='ce-label' style='margin-top:1rem'>Loaded Styles</div>",
                unsafe_allow_html=True,
            )
            badges = " ".join(badge(s) for s in styles)
            st.markdown(f"<div style='margin:0.25rem 0'>{badges}</div>", unsafe_allow_html=True)
    else:
        st.error("Cannot reach API. Check that FastAPI is running.")

    # ── Cache Stats ───────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div class='ce-label'>Cache Layer</div>", unsafe_allow_html=True)

    if cache_stats:
        enabled = cache_stats.get("enabled", False)
        file_count = cache_stats.get("file_count", 0)
        size_kb = cache_stats.get("total_size_kb", 0)
        ttl = cache_stats.get("ttl_hours", 24)
        newest = cache_stats.get("newest_hours", 0)
        oldest = cache_stats.get("oldest_hours", 0)

        st.markdown(f"""
        <div class='ce-card'>
            <div style='margin-bottom:0.75rem'>
                {badge("ENABLED" if enabled else "DISABLED", "green" if enabled else "red")}
            </div>
            <div class='ce-stat-row'>
                <div class='ce-stat'>
                    <div class='ce-stat-val'>{file_count}</div>
                    <div class='ce-stat-label'>Cached Entries</div>
                </div>
                <div class='ce-stat'>
                    <div class='ce-stat-val'>{size_kb} KB</div>
                    <div class='ce-stat-label'>Total Size</div>
                </div>
                <div class='ce-stat'>
                    <div class='ce-stat-val'>{ttl}h</div>
                    <div class='ce-stat-label'>TTL</div>
                </div>
                <div class='ce-stat'>
                    <div class='ce-stat-val'>{newest}h</div>
                    <div class='ce-stat-label'>Newest Entry</div>
                </div>
                <div class='ce-stat'>
                    <div class='ce-stat-val'>{oldest}h</div>
                    <div class='ce-stat-label'>Oldest Entry</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Cache management
        cl1, cl2, cl3 = st.columns([2, 2, 1])
        with cl1:
            hours_input = st.number_input(
                "Delete entries older than (hours)",
                min_value=0.0,
                value=0.0,
                step=1.0,
                help="0 = delete everything",
            )
        with cl3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑 Clear", use_container_width=True):
                res, s = api_post("/cache/clear", {}, timeout=10)
                # Use GET with query param instead
                api_url = st.session_state.get("api_url", DEFAULT_API_URL)
                try:
                    r = requests.post(
                        f"{api_url}/cache/clear",
                        params={"older_than_hours": hours_input},
                        timeout=10,
                    )
                    if r.status_code == 200:
                        d = r.json().get("deleted_files", 0)
                        st.success(f"Deleted {d} files.")
                    else:
                        st.error("Clear failed.")
                except Exception as e:
                    st.error(str(e))
    else:
        st.markdown(
            "<div class='ce-card'><span style='color:var(--text-dim);font-size:0.85rem'>Cache stats unavailable — check API connection.</span></div>",
            unsafe_allow_html=True,
        )

    # ── Memory Stats ──────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div class='ce-label'>Semantic Memory (ChromaDB)</div>", unsafe_allow_html=True)

    if memory_stats:
        mem_enabled = memory_stats.get("enabled", False)
        entry_count = memory_stats.get("entry_count", 0)
        threshold = memory_stats.get("similarity_threshold", 0.82)
        mem_dir = memory_stats.get("memory_dir", "memory/")

        st.markdown(f"""
        <div class='ce-card'>
            <div style='margin-bottom:0.75rem'>
                {badge("ENABLED" if mem_enabled else "DISABLED", "green" if mem_enabled else "red")}
            </div>
            <div class='ce-stat-row'>
                <div class='ce-stat'>
                    <div class='ce-stat-val'>{entry_count}</div>
                    <div class='ce-stat-label'>Stored Runs</div>
                </div>
                <div class='ce-stat'>
                    <div class='ce-stat-val'>{threshold}</div>
                    <div class='ce-stat-label'>Similarity Threshold</div>
                </div>
                <div class='ce-stat'>
                    <div class='ce-stat-val' style='font-size:0.85rem'>{mem_dir}</div>
                    <div class='ce-stat-label'>Storage Path</div>
                </div>
            </div>
            {f"<div style='margin-top:0.75rem;font-size:0.78rem;color:var(--text-dim)'>To enable: <code>uv pip install chromadb</code> then set <code>MEMORY_ENABLED=true</code> in .env</div>" if not mem_enabled else ""}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(
            "<div class='ce-card'><span style='color:var(--text-dim);font-size:0.85rem'>Memory stats unavailable.</span></div>",
            unsafe_allow_html=True,
        )

    # ── Last Run Metadata ─────────────────────────────────────
    last = st.session_state.get("last_result")
    if last and isinstance(last, dict) and last.get("metadata"):
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<div class='ce-label'>Last Pipeline Run</div>", unsafe_allow_html=True)
        meta_d = last["metadata"]
        ch = meta_d.get("cache_hits", [])
        st.markdown(f"""
        <div class='ce-card'>
            <div class='ce-stat-row'>
                <div class='ce-stat'>
                    <div class='ce-stat-val'>{meta_d.get("total_service_duration_ms",0)//1000}s</div>
                    <div class='ce-stat-label'>Duration</div>
                </div>
                <div class='ce-stat'>
                    <div class='ce-stat-val'>{meta_d.get("cached_node_count",0)}/3</div>
                    <div class='ce-stat-label'>Nodes Cached</div>
                </div>
                <div class='ce-stat'>
                    <div class='ce-stat-val'>{"Yes" if meta_d.get("memory_hit") else "No"}</div>
                    <div class='ce-stat-label'>Memory Hit</div>
                </div>
                <div class='ce-stat'>
                    <div class='ce-stat-val' style='font-size:0.82rem'>{meta_d.get("narrative_angle","—").replace("_"," ")}</div>
                    <div class='ce-stat-label'>Angle</div>
                </div>
            </div>
            <div style='margin-top:0.75rem'>
                {"".join(badge(n, "green") + " " for n in ch) if ch else "<span style='font-size:0.78rem;color:var(--text-dim)'>No cache hits</span>"}
            </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# PAGE 4 — SETTINGS
# ══════════════════════════════════════════════════════════════
elif "Settings" in page:

    st.markdown("""
    <div style='margin-bottom:1.5rem'>
        <h1>⚙️ Settings</h1>
        <div style='font-size:0.85rem;color:var(--text-dim)'>Models · Styles · Configuration reference</div>
    </div>
    """, unsafe_allow_html=True)

    # Models
    st.markdown("<div class='ce-label'>Available Models</div>", unsafe_allow_html=True)
    models_data = api_get("/models")
    if models_data:
        current = models_data.get("current_model", "—")
        st.markdown(f"""
        <div class='ce-card'>
            <div style='margin-bottom:0.75rem'>
                <span class='ce-label' style='margin-bottom:0'>Active:</span>
                <code>{current}</code>
            </div>
        """, unsafe_allow_html=True)
        for m in models_data.get("available_models", []):
            is_active = m.get("id") == current
            indicator = badge("ACTIVE", "green") if is_active else ""
            st.markdown(f"""
            <div style='padding:6px 0;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px'>
                <div style='flex:1'>
                    <div style='font-family:var(--mono);font-size:0.82rem;color:var(--text)'>{m.get("name","")}</div>
                    <div style='font-family:var(--mono);font-size:0.72rem;color:var(--text-dim)'>{m.get("id","")}</div>
                </div>
                {indicator}
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:0.78rem;color:var(--text-dim)'>Change model: edit <code>LLM_MODEL</code> in <code>.env</code> and restart.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.warning("Cannot reach API.")

    st.markdown("<hr>", unsafe_allow_html=True)

    # Creator styles
    st.markdown("<div class='ce-label'>Creator Style Profiles</div>", unsafe_allow_html=True)
    styles_d = api_get("/styles")
    if styles_d:
        for s in styles_d.get("available_styles", []):
            meta = STYLE_META.get(s, {})
            st.markdown(f"""
            <div class='ce-card' style='padding:0.9rem 1.1rem;margin-bottom:0.5rem'>
                <div style='display:flex;align-items:center;gap:10px'>
                    <span style='font-size:1.2rem'>{meta.get('icon','')}</span>
                    <div>
                        <div style='font-family:var(--mono);font-size:0.85rem;color:var(--amber);font-weight:600'>{s}</div>
                        <div style='font-size:0.78rem;color:var(--text-dim)'>{meta.get('desc','Custom style profile')}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size:0.78rem;color:var(--text-dim);margin-top:0.5rem'>
            Add a style: create <code>creator_styles/yourname.md</code> and restart the API.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Full health JSON
    st.markdown("<div class='ce-label'>Full API Health</div>", unsafe_allow_html=True)
    health = api_get("/health")
    if health:
        st.json(health)
    else:
        st.error("API offline.")

    st.markdown("<hr>", unsafe_allow_html=True)

    # Config reference
    st.markdown("<div class='ce-label'>Key .env Variables</div>", unsafe_allow_html=True)
    config_ref = {
        "HF_TOKEN": "HuggingFace access token (required)",
        "LLM_MODEL": "Model ID, e.g. Qwen/Qwen2.5-72B-Instruct:sambanova",
        "LLM_TEMPERATURE": "0.7 recommended for content generation",
        "LLM_MAX_TOKENS": "2500 covers all tasks including blog",
        "CACHE_ENABLED": "true/false — deterministic cache layer",
        "CACHE_TTL_HOURS": "24 = entries refresh after one day",
        "MEMORY_ENABLED": "true/false — requires: uv pip install chromadb",
        "MEMORY_SIMILARITY_THRESHOLD": "0.82 = 82% similarity required for match",
        "APP_ENV": "development / production",
    }
    for k, v in config_ref.items():
        st.markdown(f"""
        <div style='display:flex;align-items:baseline;gap:12px;padding:5px 0;border-bottom:1px solid var(--border)'>
            <code style='flex-shrink:0;min-width:240px'>{k}</code>
            <span style='font-size:0.78rem;color:var(--text-dim)'>{v}</span>
        </div>
        """, unsafe_allow_html=True)