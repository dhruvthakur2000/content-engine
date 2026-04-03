import asyncio
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage
 
from content_engine.backend.llm.providers import get_llm
from content_engine.backend.config.settings import get_settings
from content_engine.backend.utils.logger import get_logger
 
logger = get_logger(__name__)
settings = get_settings()
llm = get_llm()
 
 
# ============================================================
# AGENT PROMPTS
# Each prompt is laser-focused on one domain.
# Short + specific > long + vague for agent quality.
# ============================================================
 
_GIT_AGENT_PROMPT = """
You are a senior software engineer analyzing git commit history.
Your job: reconstruct EXACTLY what the developer did today.
 
GIT DATA:
{git_data}
 
Focus on:
1. What specific problem was being solved?
2. What was the approach taken?
3. Which parts of the system changed and why?
4. What does the sequence of commits reveal about the developer's process?
5. Any interesting engineering decisions visible in the commit progression?
 
Return a focused analysis (200-300 words). Be specific. Name files, functions, patterns.
No generic statements. Every sentence must come from the actual data.
"""
 
_NOTES_AGENT_PROMPT = """
You are analyzing developer notes to extract the engineering story.
 
NOTES:
{notes_data}
 
Your job: find the MOST INTERESTING thing that happened.
- What was the hardest problem?
- What was the key insight or breakthrough?
- What would a fellow engineer find most valuable to know?
- What numbers or metrics were mentioned?
 
Return a focused analysis (150-200 words).
Lead with the most interesting finding, not a summary.
"""
 
_CODE_AGENT_PROMPT = """
You are a senior engineer doing a code review for content purposes.
 
CODE:
{code_data}
 
Explain this code as if writing for a technical blog:
- What problem does it solve?
- What's technically interesting about the approach?
- What would another engineer learn from reading this?
- Any non-obvious design decisions?
 
Return 150-200 words. Technical depth matters. Skip obvious observations.
"""
 
_REFERENCE_AGENT_PROMPT = """
You are synthesizing external reference material for a technical writer.
 
REFERENCES:
{reference_data}
 
Extract and connect:
- Key technical concepts from these references
- How they relate to the developer's actual work
- What context they provide that the developer's notes don't
 
Return 150-200 words. Focus on connections and context, not summaries.
"""
 
_ORCHESTRATOR_PROMPT = """
You are an orchestrator deciding which analysis agents to activate.
 
Available agents: git_agent, notes_agent, code_agent, reference_agent
 
Input availability:
{availability}
 
Return a JSON object with your activation decisions:
{{
  "activate": ["agent1", "agent2"],
  "primary_narrative": "one sentence describing the main story to tell",
  "content_confidence": "high|medium|low"
}}
 
Rules:
- Always activate at least one agent if any input exists
- notes_agent and git_agent are most valuable — activate if available
- reference_agent only if has_urls or has_docs is true
- content_confidence = "high" if 3+ sources, "medium" if 2, "low" if 1
"""
 
 
# ============================================================
# SPECIALIST AGENTS
# Each is a simple async function: takes data, returns analysis string.
# Async because they run in parallel via asyncio.gather().
# ============================================================
 
async def git_agent(git_data: str) -> str:
    """Analyzes git history — what did the developer actually do today?"""
    if not git_data or len(git_data.strip()) < 30:
        return ""
 
    prompt = _GIT_AGENT_PROMPT.format(git_data=git_data[:3000])
 
    try:
        # asyncio.to_thread wraps the sync llm.invoke in a thread
        # so it doesn't block the event loop while waiting for the API
        response = await asyncio.to_thread(
            llm.invoke,
            [HumanMessage(content=prompt)],
            "reason",
        )
        return response.content.strip()
    except Exception as e:
        logger.error("git_agent_error", error=str(e))
        return ""
 
 
async def notes_agent(notes_data: str) -> str:
    """Extracts the most interesting engineering story from notes."""
    if not notes_data or len(notes_data.strip()) < 20:
        return ""
 
    prompt = _NOTES_AGENT_PROMPT.format(notes_data=notes_data[:2000])
 
    try:
        response = await asyncio.to_thread(
            llm.invoke,
            [HumanMessage(content=prompt)],
            "reason",
        )
        return response.content.strip()
    except Exception as e:
        logger.error("notes_agent_error", error=str(e))
        return ""
 
 
async def code_agent(code_data: str) -> str:
    """Produces a technical explanation of code for blog writing."""
    if not code_data or len(code_data.strip()) < 50:
        return ""
 
    prompt = _CODE_AGENT_PROMPT.format(code_data=code_data[:4000])
 
    try:
        response = await asyncio.to_thread(
            llm.invoke,
            [HumanMessage(content=prompt)],
            "reason",
        )
        return response.content.strip()
    except Exception as e:
        logger.error("code_agent_error", error=str(e))
        return ""
 
 
async def reference_agent(reference_data: str) -> str:
    """Synthesizes external references into useful context."""
    if not reference_data or len(reference_data.strip()) < 50:
        return ""
 
    prompt = _REFERENCE_AGENT_PROMPT.format(reference_data=reference_data[:3000])
 
    try:
        response = await asyncio.to_thread(
            llm.invoke,
            [HumanMessage(content=prompt)],
            "reason",
        )
        return response.content.strip()
    except Exception as e:
        logger.error("reference_agent_error", error=str(e))
        return ""
 
 
# ============================================================
# ORCHESTRATOR AGENT
# Decides which agents to run, then runs them.
# ============================================================
 
async def run_agents_async(
    availability: Dict[str, bool],
    git_data: str = "",
    notes_data: str = "",
    code_data: str = "",
    reference_data: str = "",
) -> Dict[str, Any]:
    """
    Runs specialist agents in parallel and collects results.
 
    This is the key V3 pattern: instead of one slow sequential
    "analyze everything" call, we run focused parallel calls.
 
    asyncio.gather() runs all coroutines concurrently — if each
    agent takes 3s, total time is ~3s not 12s.
 
    Args:
        availability: from input_detector_node
        *_data: pre-fetched content for each agent
    Returns:
        Dict mapping agent name → analysis string
    """
 
    # Build list of coroutines to run based on availability
    # We use (name, coroutine) tuples so we can map results back
    tasks: List[tuple] = []
 
    if availability.get("has_git") and git_data:
        tasks.append(("git_agent", git_agent(git_data)))
 
    if availability.get("has_notes") and notes_data:
        tasks.append(("notes_agent", notes_agent(notes_data)))
 
    if availability.get("has_code") and code_data:
        tasks.append(("code_agent", code_agent(code_data)))
 
    ref_data_combined = reference_data or ""
    if (availability.get("has_urls") or availability.get("has_docs")) and ref_data_combined:
        tasks.append(("reference_agent", reference_agent(ref_data_combined)))
 
    if not tasks:
        logger.info("no_agents_activated", reason="no_available_inputs")
        return {}
 
    # Run all agents concurrently
    names = [t[0] for t in tasks]
    coroutines = [t[1] for t in tasks]
 
    logger.info("agents_starting", agents=names, count=len(tasks))
 
    # asyncio.gather returns results in the same order as coroutines
    # return_exceptions=True means one agent failure doesn't kill others
    results_raw = await asyncio.gather(*coroutines, return_exceptions=True)
 
    agent_results: Dict[str, Any] = {}
 
    for name, result in zip(names, results_raw):
        if isinstance(result, Exception):
            # Log the exception but don't crash — other agents succeeded
            logger.error("agent_exception", agent=name, error=str(result))
            agent_results[name] = ""
        elif isinstance(result, str) and result:
            agent_results[name] = result
            logger.info("agent_completed", agent=name, output_len=len(result))
 
    return agent_results
 
 
def run_agents_sync(
    availability: Dict[str, bool],
    git_data: str = "",
    notes_data: str = "",
    code_data: str = "",
    reference_data: str = "",
) -> Dict[str, Any]:
    """
    Synchronous wrapper for run_agents_async.
 
    Why do we need this?
    The LangGraph pipeline runs synchronously. run_pipeline_service()
    is a sync function. But we want async parallel agent execution.
 
    Solution: create a new event loop just for the agent execution,
    run it to completion, then return. This is the "sync bridge"
    pattern for calling async code from sync contexts.
 
    Note: In Python 3.10+ you can use asyncio.run() directly.
    We use get_event_loop() for broader compatibility.
    """
    if not settings.agent_parallel_execution:
        # Sequential fallback — easier to debug
        return _run_agents_sequential(
            availability, git_data, notes_data, code_data, reference_data
        )
 
    try:
        # Create a fresh event loop for this call
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                run_agents_async(availability, git_data, notes_data, code_data, reference_data)
            )
        finally:
            loop.close()
    except Exception as e:
        logger.error("agent_orchestration_failed", error=str(e))
        return {}
 
 
def _run_agents_sequential(
    availability, git_data, notes_data, code_data, reference_data
) -> Dict[str, Any]:
    """Sequential fallback for debugging — runs agents one by one."""
    results = {}
 
    if availability.get("has_git") and git_data:
        try:
            response = llm.invoke(
                [HumanMessage(content=_GIT_AGENT_PROMPT.format(git_data=git_data[:3000]))],
                "reason",
            )
            results["git_agent"] = response.content.strip()
        except Exception as e:
            logger.error("sequential_git_agent_error", error=str(e))
 
    if availability.get("has_notes") and notes_data:
        try:
            response = llm.invoke(
                [HumanMessage(content=_NOTES_AGENT_PROMPT.format(notes_data=notes_data[:2000]))],
                "reason",
            )
            results["notes_agent"] = response.content.strip()
        except Exception as e:
            logger.error("sequential_notes_agent_error", error=str(e))
 
    return results