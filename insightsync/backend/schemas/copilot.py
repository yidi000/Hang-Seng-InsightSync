from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


CopilotContext = Literal["global", "market", "prospect", "signal"]


class CopilotFilters(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    prospect_id: str | None = Field(default=None, alias="prospectId")
    company_id: str | None = Field(default=None, alias="companyId")
    entity: str | None = None
    region: str | None = None
    industry: str | None = None
    signal_type: str | None = Field(default=None, alias="signalType")
    signal_subtype: str | None = Field(default=None, alias="signalSubtype")
    source: str | None = None
    dataset: str | None = None
    size_band: str | None = Field(default=None, alias="sizeBand")
    date_from: str | None = Field(default=None, alias="dateFrom")
    date_to: str | None = Field(default=None, alias="dateTo")


class CopilotChatIn(BaseModel):
    message: str = Field(min_length=1)
    conversationId: str | None = None
    context: CopilotContext = "global"
    filters: CopilotFilters = Field(default_factory=CopilotFilters)
    topK: int = Field(default=6, ge=1, le=20)


class CopilotCitationOut(BaseModel):
    evidenceId: str | None = None
    chunkId: int | None = None
    documentId: int | None = None
    title: str | None = None
    source: str | None = None
    dataset: str | None = None
    eventTime: datetime | None = None
    url: str | None = None
    snippet: str | None = None


class CopilotChatOut(BaseModel):
    answer: str
    status: str
    conversationId: str
    messageId: str
    citations: list[CopilotCitationOut] = Field(default_factory=list)
    suggestedActions: list[str] = Field(default_factory=list)
    structuredInsight: dict[str, Any] | None = None


class CopilotMessageOut(BaseModel):
    messageId: str
    role: str
    content: str
    status: str
    createdAt: datetime | None = None
    citations: list[CopilotCitationOut] = Field(default_factory=list)


class CopilotConversationOut(BaseModel):
    conversationId: str
    context: str
    prospectId: str | None = None
    title: str | None = None
    messages: list[CopilotMessageOut] = Field(default_factory=list)


class ProspectBriefOut(BaseModel):
    prospectId: str
    status: str
    brief: dict[str, Any] | None = None
    citations: list[CopilotCitationOut] = Field(default_factory=list)


class SuggestedQuestionsOut(BaseModel):
    prospectId: str
    questions: list[str]
