"""
Validation Metrics Module
Defines metrics for evaluating content quality
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ValidationMetrics:
    """Container for validation metrics"""
    
    # Text quality metrics
    word_count: int = 0
    sentence_count: int = 0
    avg_sentence_length: float = 0.0
    
    # Coherence metrics
    has_introduction: bool = False
    has_conclusion: bool = False
    topic_relevance_score: float = 0.0  # 0-1
    
    # Structure metrics
    has_citations: bool = False
    has_sections: bool = False
    section_count: int = 0
    
    # Readability metrics
    flesch_kincaid_grade: float = 0.0
    unique_words: int = 0
    vocabulary_richness: float = 0.0  # 0-1
    
    # Error metrics
    grammar_errors: int = 0
    spelling_errors: int = 0
    repetition_ratio: float = 0.0  # 0-1
    
    # Overall score
    overall_quality_score: float = 0.0  # 0-100
    is_valid: bool = False
    validation_errors: list = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "avg_sentence_length": round(self.avg_sentence_length, 2),
            "has_introduction": self.has_introduction,
            "has_conclusion": self.has_conclusion,
            "topic_relevance_score": round(self.topic_relevance_score, 2),
            "has_citations": self.has_citations,
            "has_sections": self.has_sections,
            "section_count": self.section_count,
            "flesch_kincaid_grade": round(self.flesch_kincaid_grade, 2),
            "unique_words": self.unique_words,
            "vocabulary_richness": round(self.vocabulary_richness, 2),
            "grammar_errors": self.grammar_errors,
            "spelling_errors": self.spelling_errors,
            "repetition_ratio": round(self.repetition_ratio, 2),
            "overall_quality_score": round(self.overall_quality_score, 2),
            "is_valid": self.is_valid,
            "validation_errors": self.validation_errors,
        }
    
    def print_report(self):
        """Print validation report"""
        print("\n" + "="*60)
        print("VALIDATION REPORT")
        print("="*60)
        print(f"Overall Quality Score: {self.overall_quality_score:.1f}/100")
        print(f"Is Valid: {'✅ YES' if self.is_valid else '❌ NO'}")
        print("\n📊 TEXT METRICS:")
        print(f"  - Word Count: {self.word_count}")
        print(f"  - Sentence Count: {self.sentence_count}")
        print(f"  - Avg Sentence Length: {self.avg_sentence_length:.1f} words")
        print(f"  - Unique Words: {self.unique_words}")
        print(f"  - Vocabulary Richness: {self.vocabulary_richness:.1%}")
        
        print("\n🎯 CONTENT STRUCTURE:")
        print(f"  - Has Introduction: {'✅' if self.has_introduction else '❌'}")
        print(f"  - Has Conclusion: {'✅' if self.has_conclusion else '❌'}")
        print(f"  - Has Sections: {'✅' if self.has_sections else '❌'}")
        print(f"  - Section Count: {self.section_count}")
        print(f"  - Has Citations: {'✅' if self.has_citations else '❌'}")
        
        print("\n📈 READABILITY:")
        print(f"  - Flesch-Kincaid Grade: {self.flesch_kincaid_grade:.1f}")
        print(f"  - Topic Relevance: {self.topic_relevance_score:.1%}")
        
        print("\n⚠️  QUALITY ISSUES:")
        print(f"  - Grammar Errors: {self.grammar_errors}")
        print(f"  - Spelling Errors: {self.spelling_errors}")
        print(f"  - Repetition Ratio: {self.repetition_ratio:.1%}")
        
        if self.validation_errors:
            print("\n❌ VALIDATION ERRORS:")
            for error in self.validation_errors:
                print(f"  - {error}")
        
        print("="*60 + "\n")
