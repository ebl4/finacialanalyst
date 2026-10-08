from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.clients import get_chat_model
from app.agents.prompts import QUESTION_PROMPT
from app.agents.retrieval import RetrievalAgent
from app.agents.schemas import AnswerDraft
from app.agents.untrusted import encode_untrusted_json
from app.api.schemas import QuestionRequest
from app.auth.dependencies import CurrentUser, get_current_user
from app.persistence.database import get_db
from app.persistence.models import AnalysisQuestion, Report

router = APIRouter(tags=["questions"])


@router.post("/reports/{report_id}/questions")
def ask_question(
    report_id: UUID,
    request: QuestionRequest,
    user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    report = session.scalar(
        select(Report).where(Report.id == report_id, Report.owner_id == user.id)
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")
    evidence = RetrievalAgent().invoke(
        session,
        owner_id=user.id,
        report_id=report_id,
        question=request.question.strip(),
    )
    if not evidence:
        response = {
            "answer": "There is not enough evidence in your authorized sources to answer this question.",
            "citations": [],
            "limitations": ["No relevant authorized evidence was found."],
        }
        session.add(
            AnalysisQuestion(
                report_id=report_id,
                requester_id=user.id,
                question=request.question.strip(),
                **response,
            )
        )
        session.commit()
        return response

    model: ChatOpenAI = get_chat_model()
    answer = model.with_structured_output(AnswerDraft).invoke(
        [
            ("system", QUESTION_PROMPT),
            (
                "human",
                f"Question:\n{request.question.strip()}\n\n"
                "Authorized evidence encoded as JSON data:\n"
                + encode_untrusted_json(
                    [
                        {
                            "source_id": item["id"],
                            "page_number": item["page_number"],
                            "content": item["content"],
                        }
                        for item in evidence
                    ]
                ),
            ),
        ]
    )
    citations = []
    for citation in answer.citations:
        match = next(
            (
                item
                for item in evidence
                if item["id"] == citation.source_id
                and item["page_number"] == citation.page
                and citation.excerpt.casefold() in item["content"].casefold()
            ),
            None,
        )
        if not match:
            raise HTTPException(
                status_code=502, detail="The answer contained an unverifiable citation."
            )
        citations.append(
            {
                "source_id": match["report_id"] or match["knowledge_source_id"],
                "chunk_id": match["id"],
                "label": "Financial report" if match["report_id"] else "Knowledge source",
                "page": match["page_number"],
                "excerpt": citation.excerpt,
            }
        )
    if not citations:
        response = {
            "answer": "There is not enough cited evidence to answer this question.",
            "citations": [],
            "limitations": ["The generated answer did not provide verifiable citations."],
        }
    else:
        response = {
            "answer": answer.answer,
            "citations": citations,
            "limitations": answer.limitations,
        }
    session.add(
        AnalysisQuestion(
            report_id=report_id,
            requester_id=user.id,
            question=request.question.strip(),
            **response,
        )
    )
    session.commit()
    return response


@router.get("/reports/{report_id}/questions")
def list_questions(
    report_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    report = session.scalar(
        select(Report).where(Report.id == report_id, Report.owner_id == user.id)
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    history = session.scalars(
        select(AnalysisQuestion)
        .where(AnalysisQuestion.report_id == report_id, AnalysisQuestion.requester_id == user.id)
        .order_by(AnalysisQuestion.created_at.desc())
        .limit(50)
    )
    return [
        {
            "id": item.id,
            "question": item.question,
            "answer": item.answer,
            "citations": item.citations,
            "limitations": item.limitations,
            "created_at": item.created_at,
        }
        for item in history
    ]
