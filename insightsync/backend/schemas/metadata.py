from __future__ import annotations

from pydantic import BaseModel, Field


class MetadataFiltersOut(BaseModel):
    regions: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    sizeBands: list[str] = Field(default_factory=list)
    signalTypes: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
