"""
Pydantic models for validation
Provides type-safe data validation using Pydantic v2
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Dict, Any
from enum import Enum


class ContentQualityLevel(str, Enum):
    """Enum for content quality levels"""
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"


class Paper(BaseModel):
    """Model for arXiv paper data"""
    title: str = Field(..., min_length=5, max_length=500, description="Paper title")
    summary: str = Field(..., min_length=50, max_length=5000, description="Paper summary")
    link: str = Field(..., description="Paper URL")
    
    @field_validator("link")
    @classmethod
    def validate_link(cls, v):
        """Validate that link is a proper URL"""
        if not v.startswith("http"):
            raise ValueError("Link must be a valid URL")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Deep Learning for Threat Detection",
                "summary": "This paper proposes...",
                "link": "https://arxiv.org/abs/2024.12345"
            }
        }


class ContentMetrics(BaseModel):
    """Model for content quality metrics"""
    word_count: int = Field(..., ge=100, le=10000, description="Total word count")
    sentence_count: int = Field(..., ge=5, le=1000, description="Total sentence count")
    avg_sentence_length: float = Field(..., ge=5.0, le=50.0, description="Average sentence length")
    unique_words: int = Field(..., ge=50, description="Count of unique words")
    vocabulary_richness: float = Field(..., ge=0.0, le=1.0, description="Type-token ratio")
    flesch_kincaid_grade: float = Field(..., ge=0.0, le=20.0, description="Readability grade level")
    
    @field_validator("vocabulary_richness")
    @classmethod
    def validate_vocabulary(cls, v):
        """Ensure vocabulary richness is valid"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Vocabulary richness must be between 0 and 1")
        return v


class StructureMetrics(BaseModel):
    """Model for document structure metrics"""
    has_introduction: bool = Field(..., description="Document has introduction")
    has_conclusion: bool = Field(..., description="Document has conclusion")
    has_sections: bool = Field(..., description="Document has sections")
    section_count: int = Field(..., ge=1, le=20, description="Number of sections")
    has_citations: bool = Field(..., description="Document has citations")


class QualityMetrics(BaseModel):
    """Model for quality check metrics"""
    grammar_errors: int = Field(..., ge=0, le=100, description="Grammar errors count")
    spelling_errors: int = Field(..., ge=0, le=100, description="Spelling errors count")
    repetition_ratio: float = Field(..., ge=0.0, le=1.0, description="Word repetition ratio")
    topic_relevance_score: float = Field(..., ge=0.0, le=1.0, description="Topic relevance score")


class ValidationResult(BaseModel):
    """Model for validation results"""
    is_valid: bool = Field(..., description="Whether content is valid")
    overall_quality_score: float = Field(..., ge=0.0, le=100.0, description="Overall quality score 0-100")
    quality_level: ContentQualityLevel = Field(..., description="Quality level category")
    validation_errors: List[str] = Field(default_factory=list, description="List of validation errors")
    validation_warnings: List[str] = Field(default_factory=list, description="List of validation warnings")
    content_metrics: ContentMetrics = Field(..., description="Content metrics")
    structure_metrics: StructureMetrics = Field(..., description="Structure metrics")
    quality_metrics: QualityMetrics = Field(..., description="Quality metrics")
    
    @field_validator("overall_quality_score")
    @classmethod
    def validate_score(cls, v):
        """Ensure quality score is valid"""
        if not 0.0 <= v <= 100.0:
            raise ValueError("Quality score must be between 0 and 100")
        return v


class PaperGenerationRequest(BaseModel):
    """Model for paper generation request"""
    topic: str = Field(..., min_length=3, max_length=200, description="Research topic")
    max_results: int = Field(3, ge=1, le=10, description="Max arXiv papers to fetch")
    model_name: str = Field("microsoft/phi-1_5", description="HuggingFace model to use")
    
    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v):
        """Ensure topic doesn't have invalid characters"""
        invalid_chars = ["<", ">", "{", "}", "|"]
        if any(char in v for char in invalid_chars):
            raise ValueError("Topic contains invalid characters")
        return v.strip()


class PaperGenerationResponse(BaseModel):
    """Model for paper generation response"""
    pdf_path: str = Field(..., description="Path to generated PDF")
    validation_result: ValidationResult = Field(..., description="Validation results")
    generation_time_seconds: float = Field(..., ge=0, description="Time taken to generate")
    papers_used: List[Paper] = Field(..., description="Papers used in generation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pdf_path": "outputs/Research_Paper.pdf",
                "validation_result": {
                    "is_valid": True,
                    "overall_quality_score": 85.5
                },
                "generation_time_seconds": 120.5,
                "papers_used": []
            }
        }
