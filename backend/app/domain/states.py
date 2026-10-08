from collections.abc import Mapping

REPORT_TRANSITIONS = {
    "queued": {"processing", "failed"},
    "processing": {"queued", "complete", "failed"},
    "complete": set(),
    "failed": {"queued"},
}

ANALYSIS_TRANSITIONS = {
    "queued": {"running", "failed"},
    "running": {"queued", "waiting_for_approval", "complete", "failed"},
    "waiting_for_approval": {"complete", "failed"},
    "complete": set(),
    "failed": {"queued"},
}

RECOMMENDATION_TRANSITIONS = {
    "draft": {"pending_approval"},
    "pending_approval": {"approved", "rejected"},
    "approved": {"superseded"},
    "rejected": {"superseded"},
    "superseded": set(),
}


def validate_transition(current: str, target: str, transitions: Mapping[str, set[str]]) -> str:
    current_value = str(current)
    if current_value == target:
        return target
    if target not in transitions.get(current_value, set()):
        raise ValueError(f"Invalid state transition: {current_value} -> {target}.")
    return target
