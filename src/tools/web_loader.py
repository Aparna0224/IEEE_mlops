"""
Web Content Loader for extracting and cleaning webpage content
"""

import requests
from typing import Optional
from bs4 import BeautifulSoup
from .web_search import ResearchDocument


class WebContentLoader:
    """
    Loads and extracts content from web URLs
    Handles HTML parsing and content cleaning
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def load_url(self, url: str, title: Optional[str] = None) -> Optional[ResearchDocument]:
        """
        Load and parse content from a URL
        
        Args:
            url: URL to load
            title: Optional title for the document
            
        Returns:
            ResearchDocument with extracted content, or None if failed
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Extract content from HTML
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text
            text = soup.get_text(separator=" ", strip=True)
            
            # Clean up whitespace
            text = " ".join(text.split())
            text = text[:3000]  # Limit to 3000 characters
            
            # Extract title if not provided
            if not title:
                page_title = soup.find("title")
                title = page_title.text if page_title else url.split("/")[-1]
            
            doc = ResearchDocument(
                title=title,
                source=f"Web Content",
                content=text,
                url=url,
                doc_type="webpage"
            )
            
            print(f"[INFO] Successfully loaded content from: {url}")
            return doc
            
        except requests.RequestException as e:
            print(f"[WARNING] Failed to load URL {url}: {e}")
            return None
    
    def load_github_readme(self, repo: str) -> Optional[ResearchDocument]:
        """
        Load README from a GitHub repository
        
        Args:
            repo: GitHub repository in format "owner/repo"
            
        Returns:
            ResearchDocument with README content
        """
        url = f"https://raw.githubusercontent.com/{repo}/main/README.md"
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            doc = ResearchDocument(
                title=f"GitHub: {repo}",
                source="GitHub Repository",
                content=response.text[:3000],
                url=f"https://github.com/{repo}",
                doc_type="github_readme"
            )
            return doc
        except requests.RequestException:
            # Try master branch if main doesn't exist
            url = url.replace("/main/", "/master/")
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                doc = ResearchDocument(
                    title=f"GitHub: {repo}",
                    source="GitHub Repository",
                    content=response.text[:3000],
                    url=f"https://github.com/{repo}",
                    doc_type="github_readme"
                )
                return doc
            except requests.RequestException as e:
                print(f"[WARNING] Failed to load GitHub README: {e}")
                return None
    
    def load_documentation(self, doc_url: str) -> Optional[ResearchDocument]:
        """
        Load documentation from common sources
        
        Args:
            doc_url: URL to documentation
            
        Returns:
            ResearchDocument with documentation content
        """
        return self.load_url(doc_url, title="Documentation")
