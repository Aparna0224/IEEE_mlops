"""Strict Pydantic models for final validated research paper output."""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class PaperSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class Equation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    latex: str = Field(min_length=1)
    description: Optional[str] = None


class Figure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    caption: str = Field(min_length=1)
    path: str = Field(min_length=1)
    label: str = Field(min_length=1)


class Reference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(ge=1)
    citation: str = Field(min_length=1)


class ResearchPaper(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    authors: List[str]
    abstract: str = Field(min_length=1)
    keywords: List[str]

    introduction: str = Field(min_length=1)
    related_work: str = Field(min_length=1)
    methodology: str = Field(min_length=1)
    implementation: str = Field(min_length=1)
    results: str = Field(min_length=1)
    conclusion: str = Field(min_length=1)

    equations: Optional[List[Equation]] = None
    figures: Optional[List[Figure]] = None
    references: List[Reference]
