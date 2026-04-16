"""
Pydantic-based Content Validator
Enhanced validation using Pydantic v2 models
"""

import re
from typing import List
from .pydantic_models import (
    ContentMetrics, StructureMetrics, QualityMetrics, 
    ValidationResult, ContentQualityLevel, Paper
)


class PydanticContentValidator:
    """Validates content using Pydantic models"""
    
    # Quality thresholds
    MIN_WORD_COUNT = 100
    MAX_WORD_COUNT = 5000
    MIN_SENTENCE_COUNT = 5
    MIN_UNIQUE_WORD_RATIO = 0.4
    MAX_REPETITION_RATIO = 0.15
    MIN_VOCABULARY_RICHNESS = 0.5
    
    # Keywords for structure detection
    INTRO_KEYWORDS = [
        "introduction", "background", "motivation", 
        "challenge", "problem statement", "overview"
    ]
    CONCLUSION_KEYWORDS = [
        "conclusion", "summary", "future work", 
        "findings", "impact", "implications"
    ]
    CITATION_PATTERNS = [
        r"\[[\d,\s]+\]",
        r"\(\w+\s+et\s+al\.\s*,?\s*\d{4}\)",
        r"arXiv:\d+\.\d+",
    ]
    
    def __init__(self, topic: str = ""):
        """Initialize validator with topic"""
        self.topic = topic.lower()
        self.topic_keywords = self._extract_keywords(topic)
    
    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """Extract keywords from text"""
        common_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", 
            "for", "of", "with", "by", "is", "are", "was", "were"
        }
        words = text.lower().split()
        return [w for w in words if w not in common_words and len(w) > 3]
    
    def validate(self, content: str) -> ValidationResult:
        """
        Validate content and return Pydantic ValidationResult
        
        Args:
            content: Generated paper content
            
        Returns:
            ValidationResult (Pydantic model)
        """
        # Calculate all metrics
        content_metrics = self._calculate_content_metrics(content)
        structure_metrics = self._calculate_structure_metrics(content)
        quality_metrics = self._calculate_quality_metrics(content)
        
        # Validate metrics with Pydantic
        try:
            # Validate each metric model
            content_metrics_validated = ContentMetrics(**content_metrics)
            structure_metrics_validated = StructureMetrics(**structure_metrics)
            quality_metrics_validated = QualityMetrics(**quality_metrics)
        except Exception as e:
            print(f"[WARNING] Metric validation failed: {e}")
            return self._create_error_result(str(e))
        
        # Collect validation errors and warnings
        errors = []
        warnings = []
        
        # Check structure
        if not structure_metrics["has_introduction"]:
            errors.append("Missing introduction section")
        if not structure_metrics["has_conclusion"]:
            errors.append("Missing conclusion section")
        if structure_metrics["section_count"] < 3:
            errors.append(f"Too few sections: {structure_metrics['section_count']} (min: 3)")
        
        # Check quality
        if quality_metrics["repetition_ratio"] > self.MAX_REPETITION_RATIO:
            warnings.append(
                f"High repetition ratio: {quality_metrics['repetition_ratio']:.1%}"
            )
        if quality_metrics["topic_relevance_score"] < 0.5:
            errors.append(f"Low topic relevance: {quality_metrics['topic_relevance_score']:.1%}")
        elif quality_metrics["topic_relevance_score"] < 0.7:
            warnings.append(f"Medium topic relevance: {quality_metrics['topic_relevance_score']:.1%}")
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(
            content_metrics, structure_metrics, quality_metrics
        )
        
        # Determine quality level
        quality_level = self._get_quality_level(overall_score)
        
        # Determine validity
        is_valid = overall_score >= 60.0 and len(errors) == 0
        
        # Create ValidationResult
        try:
            result = ValidationResult(
                is_valid=is_valid,
                overall_quality_score=overall_score,
                quality_level=quality_level,
                validation_errors=errors,
                validation_warnings=warnings,
                content_metrics=content_metrics_validated,
                structure_metrics=structure_metrics_validated,
                quality_metrics=quality_metrics_validated,
            )
            return result
        except Exception as e:
            print(f"[ERROR] Failed to create ValidationResult: {e}")
            return self._create_error_result(str(e))
    
    def _calculate_content_metrics(self, content: str) -> dict:
        """Calculate content metrics"""
        words = content.split()
        word_count = len(words)
        
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = len(sentences)
        
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        
        unique_words = len(set(w.lower() for w in re.findall(r'\b\w+\b', content)))
        vocabulary_richness = unique_words / word_count if word_count > 0 else 0
        
        flesch_kincaid = self._calculate_flesch_kincaid(content)
        
        return {
            "word_count": max(self.MIN_WORD_COUNT, min(word_count, self.MAX_WORD_COUNT)),
            "sentence_count": max(self.MIN_SENTENCE_COUNT, sentence_count),
            "avg_sentence_length": min(max(avg_sentence_length, 5.0), 50.0),
            "unique_words": unique_words,
            "vocabulary_richness": min(max(vocabulary_richness, 0.0), 1.0),
            "flesch_kincaid_grade": min(max(flesch_kincaid, 0.0), 20.0),
        }
    
    def _calculate_structure_metrics(self, content: str) -> dict:
        """Calculate structure metrics"""
        content_lower = content.lower()
        
        has_intro = any(kw in content_lower for kw in self.INTRO_KEYWORDS)
        has_conclusion = any(kw in content_lower for kw in self.CONCLUSION_KEYWORDS)
        
        sections = re.findall(r'^[A-Z][A-Za-z\s]+:?$', content, re.MULTILINE)
        has_sections = len(sections) > 0
        section_count = max(1, len(sections))
        
        has_citations = any(
            re.search(pattern, content) for pattern in self.CITATION_PATTERNS
        )
        
        return {
            "has_introduction": has_intro,
            "has_conclusion": has_conclusion,
            "has_sections": has_sections,
            "section_count": section_count,
            "has_citations": has_citations,
        }
    
    def _calculate_quality_metrics(self, content: str) -> dict:
        """Calculate quality metrics"""
        words = re.findall(r'\b\w+\b', content.lower())
        
        # Repetition ratio
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        common_words = {
            "the", "a", "an", "and", "or", "in", "is", "are", "was", "were"
        }
        repeated_count = sum(
            count - 1 for word, count in word_freq.items() 
            if word not in common_words and count > 2
        )
        repetition_ratio = repeated_count / len(words) if words else 0
        
        # Topic relevance
        content_keywords = self._extract_keywords(content)
        matching = set(content_keywords) & set(self.topic_keywords)
        relevance = len(matching) / len(self.topic_keywords) if self.topic_keywords else 1.0
        
        return {
            "grammar_errors": 0,  # Would require NLP library
            "spelling_errors": 0,  # Would require spell checker
            "repetition_ratio": min(max(repetition_ratio, 0.0), 1.0),
            "topic_relevance_score": min(max(relevance, 0.0), 1.0),
        }
    
    def _calculate_flesch_kincaid(self, content: str) -> float:
        """Calculate Flesch-Kincaid Grade Level"""
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        words = content.split()
        syllables = sum(self._count_syllables(word) for word in words)
        
        if not sentences or not words:
            return 0.0
        
        try:
            grade = (
                0.39 * (len(words) / len(sentences)) +
                11.8 * (syllables / len(words)) -
                15.59
            )
            return max(0.0, grade)
        except ZeroDivisionError:
            return 0.0
    
    @staticmethod
    def _count_syllables(word: str) -> int:
        """Estimate syllable count"""
        word = word.lower()
        syllables = 0
        vowels = "aeiouy"
        previous_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllables += 1
            previous_was_vowel = is_vowel
        
        if word.endswith("e"):
            syllables -= 1
        
        return max(1, syllables)
    
    def _calculate_overall_score(self, content_m, structure_m, quality_m) -> float:
        """Calculate overall quality score"""
        score = 100.0
        
        # Structure penalties
        if not structure_m["has_introduction"]:
            score -= 10
        if not structure_m["has_conclusion"]:
            score -= 10
        if structure_m["section_count"] < 3:
            score -= 10
        
        # Quality penalties
        if quality_m["repetition_ratio"] > self.MAX_REPETITION_RATIO:
            score -= 15
        if content_m["vocabulary_richness"] < self.MIN_VOCABULARY_RICHNESS:
            score -= 10
        
        # Relevance penalties
        if quality_m["topic_relevance_score"] < 0.5:
            score -= 15
        elif quality_m["topic_relevance_score"] < 0.7:
            score -= 5
        
        # Bonuses
        if structure_m["has_citations"]:
            score += 5
        if 10 < content_m["avg_sentence_length"] < 25:
            score += 5
        
        return max(0.0, min(100.0, score))
    
    @staticmethod
    def _get_quality_level(score: float) -> ContentQualityLevel:
        """Determine quality level from score"""
        if score >= 80:
            return ContentQualityLevel.EXCELLENT
        elif score >= 70:
            return ContentQualityLevel.GOOD
        elif score >= 60:
            return ContentQualityLevel.FAIR
        else:
            return ContentQualityLevel.POOR
    
    def _create_error_result(self, error_msg: str) -> ValidationResult:
        """Create error ValidationResult"""
        return ValidationResult(
            is_valid=False,
            overall_quality_score=0.0,
            quality_level=ContentQualityLevel.POOR,
            validation_errors=[error_msg],
            validation_warnings=[],
            content_metrics=ContentMetrics(
                word_count=100,
                sentence_count=5,
                avg_sentence_length=10.0,
                unique_words=50,
                vocabulary_richness=0.5,
                flesch_kincaid_grade=8.0,
            ),
            structure_metrics=StructureMetrics(
                has_introduction=False,
                has_conclusion=False,
                has_sections=False,
                section_count=1,  # Minimum valid value
                has_citations=False,
            ),
            quality_metrics=QualityMetrics(
                grammar_errors=0,
                spelling_errors=0,
                repetition_ratio=0.0,
                topic_relevance_score=0.0,
            ),
        )
