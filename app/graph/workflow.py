import uuid

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.graph import nodes as N
from app.graph.state import AgentState


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("classify", N.classify)
    g.add_node("invalid_input", N.invalid_input)
    g.add_node("firecrawl_search", N.firecrawl_search_node)
    g.add_node("version_check", N.version_check)
    g.add_node("human_confirmation", N.human_confirmation)
    g.add_node("extract", N.extract)
    g.add_node("navigate_okf", N.navigate_okf)
    g.add_node("retrieve_evidence", N.retrieve_evidence)
    g.add_node("more_evidence", N.more_evidence)
    g.add_node("impact", N.impact)
    g.add_node("final", N.final)
    g.add_node("insufficient", N.insufficient)

    g.add_edge(START, "classify")
    g.add_conditional_edges(
        "classify",
        N.classify_decision,
        {"invalid": "invalid_input", "supplied": "extract", "search": "firecrawl_search"},
    )
    g.add_edge("invalid_input", END)

    g.add_conditional_edges(
        "firecrawl_search",
        N.authority_decision,
        {"search_again": "firecrawl_search", "version_check": "version_check", "insufficient": "insufficient"},
    )
    g.add_edge("version_check", "human_confirmation")
    g.add_conditional_edges(
        "human_confirmation",
        N.confirmation_decision,
        {"confirmed": "extract", "search_again": "firecrawl_search", "insufficient": "insufficient"},
    )

    g.add_edge("extract", "navigate_okf")
    g.add_edge("navigate_okf", "retrieve_evidence")
    g.add_conditional_edges(
        "retrieve_evidence",
        N.evidence_decision,
        {"impact": "impact", "more": "more_evidence", "insufficient": "insufficient"},
    )
    g.add_edge("more_evidence", "retrieve_evidence")

    g.add_edge("impact", "final")
    g.add_edge("final", END)
    g.add_edge("insufficient", END)
    return g.compile(checkpointer=MemorySaver())


GRAPH = build_graph()


def _package(thread_id: str, result: dict) -> dict:
    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        return {
            "thread_id": thread_id,
            "status": result.get("status", []),
            "awaiting_confirmation": True,
            "confirmation": payload,
        }
    return {
        "thread_id": thread_id,
        "status": result.get("status", []),
        "awaiting_confirmation": False,
        "report": result.get("final_report", {}),
    }


def start_analysis(user_input: str, force_supplied: bool = False) -> dict:
    thread_id = str(uuid.uuid4())
    cfg = {"configurable": {"thread_id": thread_id}}
    result = GRAPH.invoke(
        {
            "user_input": user_input,
            "force_supplied": force_supplied,
            "source_search_attempts": 0,
            "evidence_iterations": 0,
            "status": [],
        },
        cfg,
    )
    return _package(thread_id, result)


def resume_analysis(thread_id: str, action: str) -> dict:
    cfg = {"configurable": {"thread_id": thread_id}}
    result = GRAPH.invoke(Command(resume=action), cfg)
    return _package(thread_id, result)
