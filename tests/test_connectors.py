"""
Unit tests for connectors module
"""

import unittest
from src.connectors import search_arxiv


class TestArxivConnector(unittest.TestCase):
    """Test cases for ArXiv connector"""
    
    def test_search_arxiv_returns_list(self):
        """Test that search_arxiv returns a list"""
        results = search_arxiv("machine learning", max_results=1)
        self.assertIsInstance(results, list)
    
    def test_search_arxiv_result_structure(self):
        """Test that search results have required fields"""
        results = search_arxiv("AI", max_results=1)
        if results:
            self.assertIn("title", results[0])
            self.assertIn("summary", results[0])
            self.assertIn("link", results[0])


if __name__ == "__main__":
    unittest.main()
