"""
Content Validator Module
Validates generated content quality and structure
"""

import re
from typing import Dict, List, Tuple
from .metrics import ValidationMetrics


class ContentValidator:
    """Validates generated paper content"""
    
    # Quality thresholds
    MIN_WORD_COUNT = 100
    MAX_WORD_COUNT = 5000
    MIN_SENTENCE_COUNT = 5
    MIN_UNIQUE_WORD_RATIO = 0.4  # 40% unique words
    MAX_REPETITION_RATIO = 0.15  # Max 15% repetition
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
        r"\[[\d,\s]+\]",  # [1], [1,2,3]
        r"\(\w+\s+et\s+al\.\s*,?\s*\d{4}\)",  # (Smith et al., 2024)
        r"arXiv:\d+\.\d+",  # arXiv:2024.12345
    ]
    
    def __init__(self, topic: str = ""):
        """Initialize validator with topic for relevance checking"""
        self.topic = topic.lower()
        self.topic_keywords = self._extract_keywords(topic)
    
    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """Extract keywords from text"""
        # Remove common words
        common_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", 
            "for", "of", "with", "by", "is", "are", "was", "were"
        }
        words = text.lower().split()
        return [w for w in words if w not in common_words and len(w) > 3]
    
    def validate(self, content: str) -> ValidationMetrics:
        """
        Perform comprehensive validation of content
        
        Args:
            content: Generated paper content
            
        Returns:
            ValidationMetrics object with all metrics
        """
        metrics = ValidationMetrics()
        metrics.validation_errors = []
        
        # 1. Basic text metrics
        self._calculate_text_metrics(content, metrics)
        
        # 2. Structure validation
        self._validate_structure(content, metrics)
        
        # 3. Content quality
        self._validate_quality(content, metrics)
        
        # 4. Relevance check
        self._check_relevance(content, metrics)
        
        # 5. Calculate overall score
        self._calculate_overall_score(metrics)
        
        return metrics
    
    def _calculate_text_metrics(self, content: str, metrics: ValidationMetrics) -> None:
        """Calculate basic text metrics"""
        # Word count
        words = content.split()
        metrics.word_count = len(words)
        
        # Sentence count
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        metrics.sentence_count = len(sentences)
        
        # Average sentence length
        if metrics.sentence_count > 0:
            metrics.avg_sentence_length = metrics.word_count / metrics.sentence_count
        
        # Unique words
        unique_words = set(w.lower() for w in re.findall(r'\b\w+\b', content))
        metrics.unique_words = len(unique_words)
        
        # Vocabulary richness (type-token ratio)
        if metrics.word_count > 0:
            metrics.vocabulary_richness = metrics.unique_words / metrics.word_count
        
        # Validate word count
        if metrics.word_count < self.MIN_WORD_COUNT:
            metrics.validation_errors.append(
                f"Content too short: {metrics.word_count} words (min: {self.MIN_WORD_COUNT})"
            )
        elif metrics.word_count > self.MAX_WORD_COUNT:
            metrics.validation_errors.append(
                f"Content too long: {metrics.word_count} words (max: {self.MAX_WORD_COUNT})"
            )
    
    def _validate_structure(self, content: str, metrics: ValidationMetrics) -> None:
        """Validate document structure"""
        content_lower = content.lower()
        
        # Check for introduction
        for keyword in self.INTRO_KEYWORDS:
            if keyword in content_lower:
                metrics.has_introduction = True
                break
        
        # Check for conclusion
        for keyword in self.CONCLUSION_KEYWORDS:
            if keyword in content_lower:
                metrics.has_conclusion = True
                break
        
        # Check for citations
        for pattern in self.CITATION_PATTERNS:
            if re.search(pattern, content):
                metrics.has_citations = True
                break
        
        # Count sections (by headers)
        sections = re.findall(r'^[A-Z][A-Za-z\s]+:?$', content, re.MULTILINE)
        metrics.has_sections = len(sections) > 0
        metrics.section_count = len(sections)
        
        # Validate structure
        if not metrics.has_introduction:
            metrics.validation_errors.append("Missing introduction section")
        if not metrics.has_conclusion:
            metrics.validation_errors.append("Missing conclusion section")
        if metrics.section_count < 3:
            metrics.validation_errors.append(
                f"Too few sections: {metrics.section_count} (min: 3)"
            )
    
    def _validate_quality(self, content: str, metrics: ValidationMetrics) -> None:
        """Validate content quality"""
        # Calculate repetition ratio
        words = re.findall(r'\b\w+\b', content.lower())
        if len(words) > 0:
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            # Find most repeated words (excluding common words)
            common_words = {
                "the", "a", "an", "and", "or", "in", "is", "are", "was", "were"
            }
            repeated_count = sum(
                count - 1 for word, count in word_freq.items() 
                if word not in common_words and count > 2
            )
            metrics.repetition_ratio = repeated_count / len(words) if words else 0
        
        # Validate repetition
        if metrics.repetition_ratio > self.MAX_REPETITION_RATIO:
            metrics.validation_errors.append(
                f"High repetition ratio: {metrics.repetition_ratio:.1%} "
                f"(max: {self.MAX_REPETITION_RATIO:.1%})"
            )
        
        # Check vocabulary richness
        if metrics.vocabulary_richness < self.MIN_VOCABULARY_RICHNESS:
            metrics.validation_errors.append(
                f"Low vocabulary richness: {metrics.vocabulary_richness:.1%} "
                f"(min: {self.MIN_VOCABULARY_RICHNESS:.1%})"
            )
        
        # Flesch-Kincaid Grade Level estimation
        metrics.flesch_kincaid_grade = self._calculate_flesch_kincaid(content)
    
    def _calculate_flesch_kincaid(self, content: str) -> float:
        """Calculate Flesch-Kincaid Grade Level"""
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        words = content.split()
        syllables = sum(self._count_syllables(word) for word in words)
        
        if not sentences or not words:
            return 0.0
        
        # FK Grade = 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
        try:
            grade = (
                0.39 * (len(words) / len(sentences)) +
                11.8 * (syllables / len(words)) -
                15.59
            )
            return max(0.0, grade)  # Grade can't be negative
        except ZeroDivisionError:
            return 0.0
    
    @staticmethod
    def _count_syllables(word: str) -> int:
        """Estimate syllable count in a word"""
        word = word.lower()
        syllables = 0
        vowels = "aeiouy"
        previous_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllables += 1
            previous_was_vowel = is_vowel
        
        # Adjust for silent 'e'
        if word.endswith("e"):
            syllables -= 1
        
        # Ensure at least 1 syllable
        return max(1, syllables)
    
    def _check_relevance(self, content: str, metrics: ValidationMetrics) -> None:
        """Check if content is relevant to the topic"""
        if not self.topic_keywords:
            metrics.topic_relevance_score = 1.0
            return
        
        content_lower = content.lower()
        content_keywords = self._extract_keywords(content_lower)
        
        # Calculate keyword overlap
        matching_keywords = set(content_keywords) & set(self.topic_keywords)
        
        if len(self.topic_keywords) > 0:
            metrics.topic_relevance_score = len(matching_keywords) / len(self.topic_keywords)
        else:
            metrics.topic_relevance_score = 1.0
        
        # Validate relevance
        if metrics.topic_relevance_score < 0.3:
            metrics.validation_errors.append(
                f"Low topic relevance: {metrics.topic_relevance_score:.1%}"
            )
    
    def _calculate_overall_score(self, metrics: ValidationMetrics) -> None:
        """Calculate overall quality score (0-100)"""
        score = 100.0
        
        # Deduct for structural issues
        if not metrics.has_introduction:
            score -= 10
        if not metrics.has_conclusion:
            score -= 10
        if metrics.section_count < 3:
            score -= 10
        
        # Deduct for quality issues
        if metrics.repetition_ratio > self.MAX_REPETITION_RATIO:
            score -= 15
        if metrics.vocabulary_richness < self.MIN_VOCABULARY_RICHNESS:
            score -= 10
        
        # Deduct for relevance
        if metrics.topic_relevance_score < 0.5:
            score -= 15
        elif metrics.topic_relevance_score < 0.7:
            score -= 5
        
        # Bonus for good structure
        if metrics.has_citations:
            score += 5
        if metrics.avg_sentence_length > 10 and metrics.avg_sentence_length < 25:
            score += 5
        
        # Cap score
        metrics.overall_quality_score = max(0.0, min(100.0, score))
        
        # Determine if valid (score >= 60)
        metrics.is_valid = metrics.overall_quality_score >= 60.0
