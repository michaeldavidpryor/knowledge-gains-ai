"""
Web Search Agent for searching the internet and retrieving information
"""

import asyncio
import aiohttp
import requests
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from .base_agent import BaseAgent


class WebSearchAgent(BaseAgent):
    """Agent specialized in web search and information retrieval"""
    
    def __init__(self):
        super().__init__(name="WebSearchAgent", model="gpt-4", temperature=0.3)
        self.search_engines = {
            "duckduckgo": "https://api.duckduckgo.com/",
            "serper": "https://google.serper.dev/search"  # Alternative API
        }
        
    async def process(self, input_data: Any) -> Dict[str, Any]:
        """Process web search request"""
        if isinstance(input_data, str):
            query = input_data
        elif isinstance(input_data, dict) and "query" in input_data:
            query = input_data["query"]
        else:
            return {"error": "Invalid input format for web search"}
            
        search_results = await self.search_web(query)
        
        # Use OpenAI to summarize and extract relevant information
        system_prompt = """You are a web search specialist. Analyze the search results provided and extract the most relevant and accurate information. 
        Provide a clear, structured summary that answers the user's query. Include source URLs when available."""
        
        summary_prompt = f"""
        Search Query: {query}
        
        Search Results:
        {self._format_search_results(search_results)}
        
        Please provide a comprehensive summary of the information found, highlighting the most relevant points for the query: "{query}"
        """
        
        summary = await self.send_message(summary_prompt, system_prompt)
        
        return {
            "query": query,
            "summary": summary,
            "raw_results": search_results,
            "source_count": len(search_results)
        }
    
    async def search_web(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Perform web search using available search engines"""
        try:
            # Using DuckDuckGo Instant Answer API (free but limited)
            return await self._search_duckduckgo(query, max_results)
        except Exception as e:
            # Fallback to simple scraping (for demo purposes)
            return await self._fallback_search(query, max_results)
    
    async def _search_duckduckgo(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Search using DuckDuckGo API"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "q": query,
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1"
                }
                
                async with session.get(self.search_engines["duckduckgo"], params=params) as response:
                    data = await response.json()
                    
                    results = []
                    
                    # Get instant answer if available
                    if data.get("AbstractText"):
                        results.append({
                            "title": data.get("Heading", "DuckDuckGo Instant Answer"),
                            "content": data.get("AbstractText"),
                            "url": data.get("AbstractURL", "")
                        })
                    
                    # Get related topics
                    for topic in data.get("RelatedTopics", [])[:max_results-1]:
                        if isinstance(topic, dict) and "Text" in topic:
                            results.append({
                                "title": topic.get("Text", "").split(" - ")[0],
                                "content": topic.get("Text", ""),
                                "url": topic.get("FirstURL", "")
                            })
                    
                    return results[:max_results]
                    
        except Exception as e:
            print(f"DuckDuckGo search failed: {e}")
            return []
    
    async def _fallback_search(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Fallback search method (simulated for demo)"""
        # In a real implementation, you might use other APIs or scraping methods
        return [{
            "title": f"Search Result for: {query}",
            "content": f"This is a simulated search result for the query '{query}'. In a production environment, this would connect to real search APIs.",
            "url": "https://example.com"
        }]
    
    def _format_search_results(self, results: List[Dict[str, str]]) -> str:
        """Format search results for OpenAI processing"""
        formatted = ""
        for i, result in enumerate(results, 1):
            formatted += f"""
Result {i}:
Title: {result.get('title', 'No title')}
Content: {result.get('content', 'No content')}
URL: {result.get('url', 'No URL')}
---
"""
        return formatted
    
    async def get_capabilities(self) -> List[str]:
        """Return web search capabilities"""
        return [
            "web_search",
            "information_retrieval", 
            "content_summarization",
            "source_verification"
        ]