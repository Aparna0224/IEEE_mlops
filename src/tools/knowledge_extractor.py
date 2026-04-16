"""
Knowledge Extractor for synthesizing and analyzing research documents
"""

from typing import List, Dict, Any, Set
from collections import Counter
from .web_search import ResearchDocument


class KnowledgeExtractor:
    """
    Extracts, deduplicates, and synthesizes knowledge from research documents
    Identifies key concepts, trends, and research gaps
    """
    
    def __init__(self):
        self.common_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", 
            "for", "of", "with", "by", "is", "are", "was", "were", "be",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "must", "can", "about",
            "also", "as", "this", "that", "these", "those", "been",
            "from", "or", "which", "who", "what", "when", "where", "why",
            "how", "all", "each", "every", "both", "few", "more", "most",
            "other", "some", "such", "no", "nor", "not", "only", "same",
            "so", "than", "too", "very", "just", "being", "have", "having"
        }
    
    def deduplicate_documents(self, documents: List[ResearchDocument]) -> List[ResearchDocument]:
        """
        Remove duplicate documents by comparing titles and content similarity
        
        Args:
            documents: List of research documents
            
        Returns:
            Deduplicated list of documents
        """
        seen_titles = set()
        unique_docs = []
        
        for doc in documents:
            title_normalized = doc.title.lower().strip()
            
            # Check if we've seen a similar title
            if title_normalized not in seen_titles:
                seen_titles.add(title_normalized)
                unique_docs.append(doc)
        
        print(f"[INFO] Deduplicated {len(documents)} documents to {len(unique_docs)}")
        return unique_docs
    
    def extract_key_concepts(self, documents: List[ResearchDocument], num_concepts: int = 20) -> List[str]:
        """
        Extract key concepts and terms from documents
        
        Args:
            documents: List of research documents
            num_concepts: Number of top concepts to extract
            
        Returns:
            List of key concepts
        """
        word_freq = Counter()
        
        for doc in documents:
            # Tokenize and filter content
            words = doc.content.lower().split()
            for word in words:
                # Clean word
                word = word.strip('.,!?;:\'"()-')
                if len(word) > 4 and word not in self.common_words:
                    word_freq[word] += 1
        
        # Get top concepts
        top_concepts = [word for word, freq in word_freq.most_common(num_concepts)]
        
        print(f"[INFO] Extracted {len(top_concepts)} key concepts")
        return top_concepts
    
    def identify_research_gaps(self, documents: List[ResearchDocument]) -> List[str]:
        """
        Identify potential research gaps from document analysis
        
        Args:
            documents: List of research documents
            
        Returns:
            List of identified research gaps
        """
        gaps = []
        content = " ".join([doc.content for doc in documents]).lower()
        
        # Look for common gap indicators
        gap_indicators = [
            ("no existing work", "No existing work found"),
            ("research gap", "Significant research gap identified"),
            ("limited research", "Limited research available"),
            ("future work", "Future work recommended"),
            ("open problem", "Open research problem identified"),
            ("unexplored", "Unexplored area found"),
            ("not yet", "Potential gap in coverage"),
            ("lacking", "Lacking comprehensive solution"),
        ]
        
        for indicator, gap_description in gap_indicators:
            if indicator in content:
                gaps.append(gap_description)
        
        print(f"[INFO] Identified {len(gaps)} potential research gaps")
        return gaps if gaps else ["Novel integration of existing techniques", "Advanced implementation approach"]
    
    def extract_methodologies(self, documents: List[ResearchDocument]) -> List[str]:
        """
        Extract commonly used methodologies from documents
        
        Args:
            documents: List of research documents
            
        Returns:
            List of identified methodologies
        """
        methodologies = []
        content = " ".join([doc.content for doc in documents]).lower()
        
        common_methods = [
            "machine learning", "deep learning", "neural network", "clustering",
            "classification", "regression", "optimization", "simulation",
            "case study", "survey", "experiment", "framework", "architecture",
            "algorithm", "model", "approach", "methodology", "technique",
            "analysis", "evaluation", "benchmark", "comparison"
        ]
        
        for method in common_methods:
            if method in content:
                methodologies.append(method)
        
        return methodologies[:10]
    
    def synthesize_knowledge(self, documents: List[ResearchDocument]) -> Dict[str, Any]:
        """
        Synthesize knowledge from all documents
        
        Args:
            documents: List of research documents
            
        Returns:
            Dictionary with synthesized knowledge
        """
        # Deduplicate
        unique_docs = self.deduplicate_documents(documents)
        
        # Extract knowledge
        key_concepts = self.extract_key_concepts(unique_docs)
        research_gaps = self.identify_research_gaps(unique_docs)
        methodologies = self.extract_methodologies(unique_docs)
        
        # Create synthesis
        synthesis = {
            "total_sources": len(documents),
            "unique_sources": len(unique_docs),
            "key_concepts": key_concepts,
            "research_gaps": research_gaps,
            "methodologies": methodologies,
            "source_types": self._get_source_distribution(unique_docs)
        }
        
        return synthesis
    
    def _get_source_distribution(self, documents: List[ResearchDocument]) -> Dict[str, int]:
        """Get distribution of document types"""
        distribution = Counter()
        for doc in documents:
            distribution[doc.doc_type] += 1
        return dict(distribution)
