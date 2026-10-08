from uuid import UUID

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.agents.analysis import AnalysisAgent, format_evidence
from app.agents.planner import PlannerAgent
from app.agents.retrieval import RetrievalAgent
from app.agents.schemas import AnalysisDraft
from app.agents.validation import ValidationAgent
from app.workflows.state import AnalysisState


def build_analysis_graph(session: Session, checkpointer: BaseCheckpointSaver):
    planner = PlannerAgent()
    retriever = RetrievalAgent()
    analyst = AnalysisAgent()
    validator = ValidationAgent()

    def plan(state: AnalysisState) -> dict:
        return {"plan": planner.invoke(state["report_text"]).model_dump()}

    def retrieve(state: AnalysisState) -> dict:
        query = "\n".join(state["plan"]["questions"])
        evidence = retriever.invoke(
            session,
            owner_id=UUID(state["owner_id"]),
            report_id=UUID(state["report_id"]),
            question=query,
        )
        return {"evidence": evidence}

    def analyze(state: AnalysisState) -> dict:
        draft = analyst.invoke(
            task="\n".join(state["plan"]["questions"]),
            evidence=format_evidence(state["evidence"]),
        )
        return {"draft": draft.model_dump()}

    def validate(state: AnalysisState) -> dict:
        draft = AnalysisDraft.model_validate(state["draft"])
        validation = validator.invoke(draft, state["evidence"])
        return {"validation": validation.model_dump()}

    workflow = StateGraph(AnalysisState)
    workflow.add_node("planner", plan)
    workflow.add_node("retrieval", retrieve)
    workflow.add_node("analysis", analyze)
    workflow.add_node("validation", validate)
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "retrieval")
    workflow.add_edge("retrieval", "analysis")
    workflow.add_edge("analysis", "validation")
    workflow.add_edge("validation", END)
    return workflow.compile(checkpointer=checkpointer)


def run_analysis(
    session: Session,
    checkpointer: BaseCheckpointSaver,
    *,
    owner_id: UUID,
    report_id: UUID,
    report_text: str,
    run_id: UUID,
) -> AnalysisState:
    graph = build_analysis_graph(session, checkpointer)
    result = graph.invoke(
        {
            "owner_id": str(owner_id),
            "report_id": str(report_id),
            "report_text": report_text[:24000],
        },
        config={"configurable": {"thread_id": str(run_id)}},
    )
    return result
