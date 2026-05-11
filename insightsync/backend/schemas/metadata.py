from __future__ import annotations

from pydantic import BaseModel, Field


class MetadataOptionOut(BaseModel):
    """Single metadata filter option with a current count."""

    name: str
    count: int


class MetadataFiltersOut(BaseModel):
    """Available filter values for frontend/API consumers."""

    regions: list[MetadataOptionOut] = Field(default_factory=list)
    segments: list[MetadataOptionOut] = Field(default_factory=list)
    industries: list[MetadataOptionOut] = Field(default_factory=list)
    signal_types: list[MetadataOptionOut] = Field(default_factory=list)
    sources: list[MetadataOptionOut] = Field(default_factory=list)
    datasets: list[MetadataOptionOut] = Field(default_factory=list)
