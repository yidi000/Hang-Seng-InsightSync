from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from insightsync.backend.core.config import get_settings
from insightsync.backend.db.session import get_db
from insightsync.backend.schemas.copilot import (
    CopilotChatIn,
    CopilotChatOut,
    CopilotCitationOut,
    CopilotConversationOut,
    CopilotMessageOut,
    ProspectBriefOut,
    SuggestedQuestionsOut,
)
from insightsync.backend.services.copilot_service import CopilotService

router = APIRouter(prefix="/api/copilot", tags=["copilot"])


def _citation(item: dict) -> CopilotCitationOut:
    return CopilotCitationOut(
        evidenceId=item.get("evidence_id"),
        chunkId=item.get("chunk_id"),
        documentId=item.get("document_id"),
        title=item.get("title"),
        source=item.get("source"),
        dataset=item.get("dataset"),
        eventTime=item.get("event_time"),
        url=item.get("url"),
        snippet=item.get("snippet"),
    )


@router.post("/chat", response_model=CopilotChatOut)
def chat(payload: CopilotChatIn, db: Session = Depends(get_db)) -> CopilotChatOut:
    """Chat with the backend Copilot using curated evidence and GLM-compatible generation."""

    service = CopilotService(db, get_settings())
    result = service.chat(
        message=payload.message,
        conversation_id=payload.conversationId,
        context=payload.context,
        filters=payload.filters.model_dump(exclude_none=True),
        top_k=payload.topK,
    )
    db.commit()
    return CopilotChatOut(
        answer=result["answer"],
        status=result["status"],
        conversationId=result["conversation_id"],
        messageId=result["message_id"],
        citations=[_citation(item) for item in result.get("citations", [])],
        suggestedActions=result.get("suggested_actions", []),
        structuredInsight=result.get("structured_insight"),
    )


@router.get("/conversations/{conversation_id}", response_model=CopilotConversationOut)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)) -> CopilotConversationOut:
    """Return a Copilot conversation and citations."""

    result = CopilotService(db, get_settings()).get_conversation(conversation_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": {"code": "NOT_FOUND", "message": "Conversation not found"}})
    return CopilotConversationOut(
        conversationId=result["conversation_id"],
        context=result["context"],
        prospectId=result.get("prospect_id"),
        title=result.get("title"),
        messages=[
            CopilotMessageOut(
                messageId=item["message_id"],
                role=item["role"],
                content=item["content"],
                status=item["status"],
                createdAt=item.get("created_at"),
                citations=[_citation(citation) for citation in item.get("citations", [])],
            )
            for item in result.get("messages", [])
        ],
    )


@router.post("/prospect/{prospect_id}/brief", response_model=ProspectBriefOut)
def prospect_brief(prospect_id: str, db: Session = Depends(get_db)) -> ProspectBriefOut:
    """Generate a prospect-scoped outreach brief."""

    result = CopilotService(db, get_settings()).prospect_brief(prospect_id)
    db.commit()
    return ProspectBriefOut(
        prospectId=prospect_id,
        status=result["status"],
        brief=result.get("structured_insight"),
        citations=[_citation(item) for item in result.get("citations", [])],
    )


@router.post("/prospect/{prospect_id}/questions", response_model=SuggestedQuestionsOut)
def prospect_questions(prospect_id: str, db: Session = Depends(get_db)) -> SuggestedQuestionsOut:
    """Return suggested Copilot questions for a prospect."""

    return SuggestedQuestionsOut(
        prospectId=prospect_id,
        questions=CopilotService(db, get_settings()).suggested_questions(prospect_id),
    )
