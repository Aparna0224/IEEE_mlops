"""
ArXiv API Connector
Fetches research papers from arXiv based on search queries
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any


def search_arxiv(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search for research papers on arXiv.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 3)
        
    Returns:
        List of dictionaries containing:
            - title: Paper title
            - summary: Paper summary
            - link: Link to the paper
    """
    max_results = int(max_results)
    url = f"https://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={max_results}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch from arXiv: {e}")
        return []
    
    soup = BeautifulSoup(response.text, "lxml-xml")
    results = []
    
    for entry in soup.find_all("entry"):
        try:
            results.append({
                "title": entry.title.text,
                "summary": entry.summary.text.strip(),
                "link": entry.id.text
            })
        except AttributeError as e:
            print(f"[WARNING] Failed to parse entry: {e}")
            continue
    
    return results
