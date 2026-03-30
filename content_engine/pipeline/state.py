from typing import List, Dict, Any, Optional
class PipelineState:
    def __init__(self):

        self.raw_notes: Optional[str] = None
        self.raw_git_log: Optional[str] = None
        self.platforms: Optional[List[str]] = None
        self.author_name: Optional[str] = None
        self.style: Optional[str] = None
        self.extra_material: Optional[str] = None
        self.memory_context: Optional[str] = None

        self.blog_urls: Optional[List[str]] = None
        self.code_context: Optional[str] = None
        self.transcript: Optional[str] = None
        self.doc_references: Optional[str] = None
        self.blog_style: Optional[str] = None
        self.git_auto_result: Optional[str] = None
        self.url_summaries: Optional[str] = None

        # ----------------------------------------------------------
        # INPUT AVAILABILITY MAP
        # Written by input_detector_node (runs first in pipeline).
        # {"has_notes": True, "has_git": False, "source_count": 1, ...}
        # All downstream nodes read this instead of re-checking inputs.
        # ----------------------------------------------------------
        self.input_availability: Dict[str, bool] = {}

        # ----------------------------------------------------------
        # INTERMEDIATE FIELDS
        # Each parsing node writes one. context_builder fuses them all.
        # ----------------------------------------------------------
        self.parsed_notes: Optional[str] = None
        self.parsed_git: Optional[str] = None
        self.parsed_code: Optional[str] = None
        self.parsed_references: Optional[str] = None
        self.context: Optional[str] = None          # Unified context — most nodes read this
        self.narrative_angle: Optional[str] = None
        self.hook: Optional[str] = None
        self.key_detail: Optional[str] = None
        self.style_guide: Optional[str] = None      # Loaded creator .md content
        self.blog_blueprint: Optional[str] = None   # Stage-1 blog plan
        self.fusion_context: Optional[str] = None

        # ----------------------------------------------------------
        # AGENT FIELDS — V3 multi-agent
        # orchestrator.py writes agent_results after parallel execution.
        # context_builder reads it to enrich unified context.
        # ----------------------------------------------------------
        self.agent_results: Dict[str, Any] = {}
        self.orchestration_plan: Dict[str, Any] = {}

        # ----------------------------------------------------------
        # SECURITY FIELDS — Phase 5
        # Written first by security_node.
        # graph.py reads security_check["passed"] to short-circuit.
        # ----------------------------------------------------------
        self.security_check: Dict[str, Any] = {}

        # ----------------------------------------------------------
        # EVALUATION FIELDS — Phase 4
        # evaluator_node writes after post_generator.
        # graph.py reads evaluation_passed for the regen loop.
        # ----------------------------------------------------------
        self.evaluation_scores: Dict[str, Any] = {}
        self.evaluation_passed: Optional[bool] = None
        self.regeneration_count: int = 0

        # ----------------------------------------------------------
        # OUTPUT FIELDS
        # post_generator writes generated_posts.
        # humanize_node overwrites with polished versions.
        # ----------------------------------------------------------
        self.generated_posts: Dict[str, str] = {}
        self.metadata: Dict[str, Any] = {}

        # ----------------------------------------------------------
        # PIPELINE CONTROL
        # ----------------------------------------------------------
        self.cache_hits: List[str] = []
        self.memory_hit: bool = False
        self.errors: List[str] = []

    # ============================================================
    # DICT-LIKE INTERFACE
    # Every node calls state.get("key", default).
    # getattr(self, key, default) is Python's attribute lookup with fallback —
    # same behavior as dict.get(key, default).
    # ============================================================

    def get(self, key: str, default=None):
        return getattr(self, key, default)

    def set(self, key: str, value):
        setattr(self, key, value)

    def update(self, data: Dict[str, Any]):
        """
        Merge a partial dict into this state.
        Called by graph.py adapter after every node runs.
        Nodes return partial dicts — update() applies them.

        List fields (cache_hits, errors) are ACCUMULATED not replaced.
        This matches LangGraph's TypedDict reducer behavior for lists.
        """
        for key, value in data.items():
            if key == "cache_hits" and isinstance(value, list):
                # Accumulate cache hits — deduplicate
                existing = list(self.cache_hits or [])
                for item in value:
                    if item not in existing:
                        existing.append(item)
                self.cache_hits = existing
            elif key == "errors" and isinstance(value, list):
                # Accumulate errors — extend
                self.errors = list(self.errors or []) + value
            else:
                setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to plain dict for LangGraph invoke() and API responses.
        __dict__ returns all instance attributes. .copy() prevents mutation.
        """
        return self.__dict__.copy()

    def __repr__(self) -> str:
        """Shows only non-empty fields — useful for debugging."""
        non_empty = {
            k: v for k, v in self.__dict__.items()
            if v is not None and v != {} and v != [] and v != ""
        }
        return f"PipelineState(fields={list(non_empty.keys())})"