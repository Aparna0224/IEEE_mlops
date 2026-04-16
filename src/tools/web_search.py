"""
Web Search Tool for researching topics across the internet
"""

import requests
from typing import List, Dict, Any
from datetime import datetime


class ResearchDocument:
    """Structured research document"""
    def __init__(self, title: str, source: str, content: str, url: str, doc_type: str = "web"):
        self.title = title
        self.source = source
        self.content = content
        self.url = url
        self.doc_type = doc_type
        self.fetched_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "source": self.source,
            "content": self.content,
            "url": self.url,
            "doc_type": self.doc_type,
            "fetched_at": self.fetched_at
        }


class WebSearchTool:
    """
    Web Search Tool using DuckDuckGo (no API key required)
    Returns structured research documents
    """
    
    def __init__(self):
        self.search_url = "https://api.duckduckgo.com"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def search(self, query: str, num_results: int = 5) -> List[ResearchDocument]:
        """
        Search the web using DuckDuckGo API
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            List of ResearchDocument objects
        """
        try:
            params = {
                "q": query,
                "format": "json",
                "no_html": 1,
                "no_redirect": 1
            }
            
            response = self.session.get(self.search_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            documents = []
            
            # Extract results from DuckDuckGo API
            for result in data.get("Results", [])[:num_results]:
                doc = ResearchDocument(
                    title=result.get("Title", ""),
                    source="DuckDuckGo Web Search",
                    content=result.get("Abstract", ""),
                    url=result.get("FirstURL", ""),
                    doc_type="web_article"
                )
                documents.append(doc)
            
            # Also try to fetch snippets from related topics
            for topic in data.get("RelatedTopics", [])[:2]:
                if "FirstURL" in topic:
                    doc = ResearchDocument(
                        title=topic.get("Text", ""),
                        source="DuckDuckGo Related Topic",
                        content=topic.get("Text", ""),
                        url=topic.get("FirstURL", ""),
                        doc_type="related_topic"
                    )
                    if len(documents) < num_results:
                        documents.append(doc)
            
            print(f"[INFO] Web search completed. Found {len(documents)} documents.")
            return documents
            
        except requests.RequestException as e:
            print(f"[ERROR] Web search failed: {e}")
            return []
    
    def search_academic(self, query: str, num_results: int = 10) -> List[ResearchDocument]:
        """
        Search for academic content
        Uses Scholar-like approach by searching Google Scholar via external service
        """
        # For academic search, we'll search with keywords that favor academic content
        scholar_query = f"{query} site:scholar.google.com OR site:researchgate.net OR site:arxiv.org"
        return self.search(scholar_query, num_results)
