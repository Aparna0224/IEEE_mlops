"""
Enhanced ArXiv Search Tool for academic paper retrieval
"""

import requests
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from .web_search import ResearchDocument


class ArxivSearchTool:
    """
    Enhanced ArXiv search tool with structured document returns
    Searches research papers and returns formatted documents
    """
    
    def __init__(self):
        self.base_url = "https://export.arxiv.org/api/query"
        self.session = requests.Session()
    
    def search(self, query: str, num_results: int = 10, category: str = "cs") -> List[ResearchDocument]:
        """
        Search arXiv for research papers
        
        Args:
            query: Search query (title, authors, abstract)
            num_results: Number of papers to return
            category: arXiv category (cs, math, physics, etc.)
            
        Returns:
            List of ResearchDocument objects with paper information
        """
        try:
            # Build search query for arXiv API
            search_query = f"all:{query}"
            if category:
                search_query += f" AND cat:{category}"
            
            params = {
                "search_query": search_query,
                "start": 0,
                "max_results": num_results,
                "sortBy": "relevance",
                "sortOrder": "descending"
            }
            
            response = self.session.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            
            # Parse XML response
            soup = BeautifulSoup(response.text, "lxml-xml")
            documents = []
            
            for entry in soup.find_all("entry"):
                try:
                    # Extract paper metadata
                    paper_id = entry.id.text.split('/abs/')[-1] if entry.id else "unknown"
                    title = entry.title.text.strip() if entry.title else "Unknown Title"
                    summary = entry.summary.text.strip() if entry.summary else ""
                    published = entry.published.text if entry.published else ""
                    
                    # Extract authors
                    authors = []
                    for author in entry.find_all("author"):
                        name = author.find("name")
                        if name:
                            authors.append(name.text)
                    
                    # Create structured document
                    content = f"""
Title: {title}
Authors: {', '.join(authors)}
Published: {published}
arXiv ID: {paper_id}

Abstract:
{summary}
"""
                    
                    doc = ResearchDocument(
                        title=title,
                        source=f"arXiv ({paper_id})",
                        content=content,
                        url=f"https://arxiv.org/abs/{paper_id}",
                        doc_type="academic_paper"
                    )
                    documents.append(doc)
                    
                except (AttributeError, IndexError) as e:
                    print(f"[WARNING] Failed to parse arXiv entry: {e}")
                    continue
            
            print(f"[INFO] ArXiv search completed. Found {len(documents)} papers.")
            return documents
            
        except requests.RequestException as e:
            print(f"[ERROR] ArXiv search failed: {e}")
            return []
    
    def search_by_topic(self, topic: str, num_results: int = 15) -> List[ResearchDocument]:
        """
        Search arXiv by topic with multiple relevant queries
        """
        all_papers = []
        queries = [
            topic,
            f"survey {topic}",
            f"review {topic}"
        ]
        
        papers_per_query = max(5, num_results // len(queries))
        
        for query in queries:
            papers = self.search(query, num_results=papers_per_query)
            all_papers.extend(papers)
        
        # Remove duplicates by title
        seen_titles = set()
        unique_papers = []
        for paper in all_papers:
            if paper.title not in seen_titles:
                seen_titles.add(paper.title)
                unique_papers.append(paper)
        
        return unique_papers[:num_results]
