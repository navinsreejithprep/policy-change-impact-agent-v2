from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    user_input: str
    input_invalid: bool
    force_supplied: bool

    regulation_supplied: bool
    regulation_text: str

    source_candidates: list[dict[str, Any]]
    selected_source: dict[str, Any]
    tried_domains: list[str]
    source_search_attempts: int
    max_source_search_attempts: int
    search_note: str

    confirmation_payload: dict[str, Any]
    human_confirmation_action: str

    requirements: list[dict[str, Any]]
    injection_detected: bool
    injection_flags: list[str]

    knowledge_results: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    evidence_gaps: list[str]
    evidence_iterations: int
    max_evidence_iterations: int

    impacts: list[dict[str, Any]]
    assumptions: list[str]
    actions: list[dict[str, Any]]

    status: list[str]
    final_report: dict[str, Any]
