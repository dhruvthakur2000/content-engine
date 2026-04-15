# ============================================================
# test_pipeline.py
# Simple direct test for your LangGraph pipeline
# ============================================================

from content_engine.pipeline.graph import get_pipeline
from content_engine.pipeline.state import PipelineState


def run_test():
    print("\n Running Pipeline Test...\n")
    # Debug: Print loaded Hugging Face token
    from content_engine.backend.config.settings import get_settings
    settings = get_settings()
    print(f"[DEBUG] Loaded HF_TOKEN: {settings.hf_token!r}")

    # ---------------------------------------------
    # Step 1: Create initial state
    # ---------------------------------------------
    state = PipelineState()

    state.update({
        "raw_notes": "Reduced websocket latency from 820ms to 580ms by fixing buffer flushing.",
        "raw_git_log": "fix: websocket buffer optimization",
        "platforms": ["linkedin"],
        "author_name": "Dhruv",
        "style": "dhruv_default",
        "extra_material": "",
    })

    # ---------------------------------------------
    # Step 2: Run pipeline
    # ---------------------------------------------
    try:
        from content_engine.pipeline.graph import invoke_pipeline
        final_state = invoke_pipeline(state)

    except Exception as e:
        print(" PIPELINE FAILED")
        print(e)
        return

    # ---------------------------------------------
    # Step 3: Print outputs
    # ---------------------------------------------
    print("\n PIPELINE SUCCESS\n")

    print(" Generated Posts:\n")
    posts = final_state.get("generated_posts", {})

    for platform, content in posts.items():
        print(f"\n--- {platform.upper()} ---\n")
        print(content[:500])  # avoid flooding terminal

    print("\n Metadata:\n")
    print(final_state.get("metadata", {}))

    print("\n Cache Hits:")
    print(final_state.get("cache_hits", []))

    print("\n Regeneration Count:")
    print(final_state.get("regeneration_count", 0))

    print("\n Errors:")
    print(final_state.get("errors", []))


if __name__ == "__main__":
    run_test()