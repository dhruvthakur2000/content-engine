from content_engine.pipeline.state import PipelineState
from content_engine.pipeline.utils.node_wrapper import pipeline_node
from content_engine.backend.utils.logger import get_logger

logger = get_logger(__name__)
NODE_NAME = "input_detector"


MIN_NOTES_LENGTH = 20
MIN_GIT_LENGTH = 30
MIN_EXTRA_LENGTH = 20


@pipeline_node(NODE_NAME)
def input_detector_node(state: PipelineState):

    raw_notes = str(state.get("raw_notes", "")).strip()
    raw_git = str(state.get("raw_git_log", "")).strip()
    extra = str(state.get("extra_material", "")).strip()

    has_notes = bool(raw_notes and len(raw_notes) > MIN_NOTES_LENGTH)
    has_git = bool(raw_git and len(raw_git) > MIN_GIT_LENGTH)
    has_extra = bool(extra and len(extra) > MIN_EXTRA_LENGTH)

    availability = {
        "has_notes": has_notes,
        "has_git": has_git,
        "has_extra": has_extra,
        "has_any_input": any([has_notes, has_git, has_extra]),
        "source_count": sum([has_notes, has_git, has_extra]),
    }

    logger.info(
        "input_detection_complete",
        availability=availability,
        source_count=availability["source_count"],
    )

    errors = state.get("errors", [])

    if not availability["has_any_input"]:
        errors = errors + ["No usable input detected"]

    return {
        "input_availability": availability,
        "errors": errors,
    }