from langchain_core.messages import HumanMessage
 
from content_engine.pipeline.state import PipelineState
from content_engine.pipeline.utils.node_wrapper import pipeline_node
from content_engine.backend.llm.providers import get_llm
from content_engine.backend.config.settings import get_settings
from content_engine.backend.utils.logger import get_logger
 
logger = get_logger(__name__)
settings = get_settings()
llm = get_llm()
 
_EVAL_PROMPT = """
You are evaluating AI-generated content for quality. Score each metric on a 1-10 scale.
Be strict — this content will be published publicly.
 
PLATFORM: {platform}
CONTENT:
{content}
 
Score these three metrics:
 
1. SPECIFICITY (1-10):
   - 10 = mentions real tools, actual numbers, file names, error messages
   - 5  = some specifics but also some vague statements
   - 1  = completely generic, could apply to any project
   Is this content specific to real engineering work, or generic filler?
 
2. AI_TONE (1-10):
   - 1  = sounds completely human-written, natural rhythm
   - 5  = some AI patterns but mostly readable
   - 10 = heavy AI tone: "delve into", "robust", "seamlessly", formulaic structure
   Does this sound like it was written by ChatGPT?
   (LOWER score = better for this metric)
 
3. HOOK_STRENGTH (1-10):
   - 10 = opening line makes an engineer stop scrolling immediately
   - 5  = decent but not compelling
   - 1  = generic opener, no one would stop for this
 
Return ONLY this format (no other text):
SPECIFICITY: <number>
AI_TONE: <number>
HOOK_STRENGTH: <number>
VERDICT: PASS or FAIL
MAIN_ISSUE: <one sentence — the most important thing to improve>
"""
 
 
@pipeline_node("evaluator")
def evaluator_node(state: PipelineState) -> PipelineState:
    """
    Scores generated content and decides whether to regenerate.
 
    Reads:  state["generated_posts"]
    Writes: state["evaluation_scores"], state["evaluation_passed"],
            state["regeneration_count"]
    """
 
    # Skip if evaluation is disabled in settings
    if not settings.eval_enabled:
        return {"evaluation_passed": True, "evaluation_scores": {}}
 
    generated_posts = state.get("generated_posts", {})
 
    if not generated_posts:
        return {"evaluation_passed": False, "evaluation_scores": {}}
 
    scores: dict = {}
    all_passed = True
 
    for platform, content in generated_posts.items():
        # Don't evaluate error strings or empty content
        if not content or content.startswith("["):
            scores[platform] = {"error": "no_content_to_evaluate"}
            continue
 
        prompt = _EVAL_PROMPT.format(platform=platform, content=content[:2000])
 
        try:
            response = llm.invoke([HumanMessage(content=prompt)], task="eval")
            raw = response.content.strip()
 
            # Parse the structured response
            platform_scores = _parse_eval_response(raw)
            scores[platform] = platform_scores
 
            # Check against thresholds from settings
            platform_passed = _check_thresholds(platform_scores)
            scores[platform]["passed"] = platform_passed
 
            if not platform_passed:
                all_passed = False
                logger.info(
                    "eval_failed",
                    platform=platform,
                    scores=platform_scores,
                    main_issue=platform_scores.get("main_issue", "unknown"),
                )
            else:
                logger.info("eval_passed", platform=platform, scores=platform_scores)
 
        except Exception as e:
            logger.error("evaluator_error", platform=platform, error=str(e))
            scores[platform] = {"error": str(e), "passed": True}  # Don't block on eval error
 
    regen_count = state.get("regeneration_count", 0)
 
    # Should we regenerate?
    # Yes if: eval failed AND we haven't hit the max regen limit
    should_regenerate = (
        not all_passed
        and regen_count < settings.eval_max_regenerations
    )
 
    if should_regenerate:
        # Prepare regeneration feedback — tell post_generator what to fix
        feedback = _build_regen_feedback(scores)
        logger.info("triggering_regeneration", attempt=regen_count + 1, feedback=feedback[:100])
        return {
            "evaluation_scores": scores,
            "evaluation_passed": False,
            "regeneration_count": regen_count + 1,
            # Inject feedback into metadata so post_generator can read it
            "metadata": {**(state.get("metadata", {})), "eval_feedback": feedback},
        }
 
    if not all_passed:
        logger.info(
            "eval_failed_max_retries_reached",
            regen_count=regen_count,
            note="Returning best-effort content",
        )
 
    return {
        "evaluation_scores": scores,
        "evaluation_passed": True,   # Force pass after max retries
        "regeneration_count": regen_count,
    }
 
 
def _parse_eval_response(raw: str) -> dict:
    """Parse the structured evaluation response into a dict."""
    result = {}
 
    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("SPECIFICITY:"):
            try:
                result["specificity"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                result["specificity"] = 5
        elif line.startswith("AI_TONE:"):
            try:
                result["ai_tone"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                result["ai_tone"] = 5
        elif line.startswith("HOOK_STRENGTH:"):
            try:
                result["hook_strength"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                result["hook_strength"] = 5
        elif line.startswith("MAIN_ISSUE:"):
            result["main_issue"] = line.split(":", 1)[1].strip()
        elif line.startswith("VERDICT:"):
            result["verdict"] = line.split(":", 1)[1].strip()
 
    return result
 
 
def _check_thresholds(scores: dict) -> bool:
    """Check if scores meet minimum quality thresholds."""
    specificity = scores.get("specificity", 5)
    ai_tone = scores.get("ai_tone", 5)
    hook = scores.get("hook_strength", 5)
 
    # All three conditions must pass
    return (
        specificity >= settings.eval_min_specificity
        and ai_tone <= settings.eval_max_ai_tone
        and hook >= 5  # Hook minimum: 5/10
    )
 
 
def _build_regen_feedback(scores: dict) -> str:
    """Build actionable feedback string for regeneration."""
    issues = []
    for platform, s in scores.items():
        if not s.get("passed", True):
            issue = s.get("main_issue", "")
            spec = s.get("specificity", "?")
            tone = s.get("ai_tone", "?")
            issues.append(
                f"{platform}: specificity={spec}/10, ai_tone={tone}/10. Fix: {issue}"
            )
    return " | ".join(issues) if issues else "Improve specificity and reduce AI tone."