"""
Unit tests for validators module
"""

import unittest
from src.validators import ContentValidator, ValidationMetrics


class TestContentValidator(unittest.TestCase):
    """Test cases for ContentValidator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = ContentValidator(topic="machine learning AI")
    
    def test_validate_good_content(self):
        """Test validation of good content"""
        good_content = """
        Introduction: Machine learning is a subfield of artificial intelligence.
        Background and motivation for this research are discussed.
        
        Methodology: We propose a novel approach to AI-driven systems.
        Implementation details are provided below.
        
        Results: Our experiments show promising results [1].
        The performance improved significantly.
        
        Related Work: Previous studies in machine learning have shown...
        Different approaches to AI challenges are considered.
        
        Discussion: The findings have important implications for AI.
        This research contributes to the field of machine learning.
        
        Conclusion: This study demonstrates the effectiveness of our approach.
        Future work should explore additional machine learning techniques.
        References [1,2,3] support these findings.
        """
        
        metrics = self.validator.validate(good_content)
        
        self.assertIsNotNone(metrics)
        self.assertGreater(metrics.word_count, 0)
        self.assertGreater(metrics.sentence_count, 0)
        self.assertTrue(metrics.has_introduction)
        self.assertTrue(metrics.has_conclusion)
    
    def test_validate_short_content(self):
        """Test validation of too short content"""
        short_content = "This is too short."
        
        metrics = self.validator.validate(short_content)
        
        self.assertFalse(metrics.is_valid)
        self.assertIn("too short", metrics.validation_errors[0].lower())
    
    def test_validate_missing_structure(self):
        """Test validation of content missing structure"""
        content = "Some random text without proper structure. More text here."
        
        metrics = self.validator.validate(content)
        
        # Should have some validation errors about structure
        has_structure_error = any(
            "introduction" in str(e).lower() or "conclusion" in str(e).lower()
            for e in metrics.validation_errors
        )
        self.assertTrue(has_structure_error or not metrics.is_valid)
    
    def test_syllable_counting(self):
        """Test syllable counting"""
        # Test various words
        self.assertEqual(ContentValidator._count_syllables("hello"), 2)
        self.assertEqual(ContentValidator._count_syllables("computer"), 3)
        self.assertEqual(ContentValidator._count_syllables("artificial"), 4)
    
    def test_metrics_to_dict(self):
        """Test metrics to dictionary conversion"""
        metrics = ValidationMetrics()
        metrics.word_count = 500
        metrics.overall_quality_score = 85.0
        
        metrics_dict = metrics.to_dict()
        
        self.assertIsInstance(metrics_dict, dict)
        self.assertEqual(metrics_dict["word_count"], 500)
        self.assertEqual(metrics_dict["overall_quality_score"], 85.0)


class TestValidationMetrics(unittest.TestCase):
    """Test cases for ValidationMetrics"""
    
    def test_metrics_initialization(self):
        """Test metrics initialization"""
        metrics = ValidationMetrics()
        
        self.assertEqual(metrics.word_count, 0)
        self.assertFalse(metrics.is_valid)
        self.assertIsNotNone(metrics.validation_errors)
        self.assertEqual(len(metrics.validation_errors), 0)
    
    def test_metrics_post_init(self):
        """Test post-init validation"""
        metrics = ValidationMetrics(word_count=100)
        
        # validation_errors should be initialized as empty list
        self.assertIsNotNone(metrics.validation_errors)
        self.assertIsInstance(metrics.validation_errors, list)


if __name__ == "__main__":
    unittest.main()
