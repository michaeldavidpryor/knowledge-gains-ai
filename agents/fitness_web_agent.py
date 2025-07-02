"""
Fitness Web Search Agent for Knowledge Gains - Specialized for fitness and exercise research
"""

import asyncio
import json
from typing import Any, Dict, List
from urllib.parse import quote_plus

import aiohttp
from bs4 import BeautifulSoup

from .base_agent import BaseAgent


class FitnessWebAgent(BaseAgent):
    """Specialized web search agent for fitness and exercise information"""

    def __init__(self):
        super().__init__(name="FitnessWebAgent", model="gpt-4", temperature=0.3)
        self.search_engines = {
            "duckduckgo": self._search_duckduckgo,
            "fitness_sites": self._search_fitness_sites,
        }

        # Fitness-specific search sources
        self.fitness_sites = [
            "strongerbyscience.com",
            "athleanx.com",
            "t-nation.com",
            "bodybuilding.com",
            "muscleandstrength.com",
            "jeremyethier.com",
            "jeffnippard.com",
        ]

    async def process(self, input_data: Any) -> Dict[str, Any]:
        """Process web search requests for fitness information"""

        if isinstance(input_data, str):
            search_query = input_data
            search_type = "general"
        elif isinstance(input_data, dict):
            search_query = input_data.get("query", "")
            search_type = input_data.get("type", "general")
        else:
            return {"error": "Invalid input format for fitness web agent"}

        if not search_query:
            return {"error": "No search query provided"}

        # Enhance query with fitness context
        enhanced_query = self._enhance_fitness_query(search_query, search_type)

        # Perform searches using multiple sources
        search_tasks = [
            self._search_duckduckgo(enhanced_query),
            self._search_fitness_sites(enhanced_query),
        ]

        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Combine and analyze results
        combined_results = []
        for i, result in enumerate(search_results):
            if isinstance(result, Exception):
                print(f"Search engine {i} failed: {result}")
                continue
            if isinstance(result, list):
                combined_results.extend(result)

        if not combined_results:
            return {"error": "No search results found", "query": enhanced_query}

        # Analyze and synthesize fitness information
        analysis = await self._analyze_fitness_results(
            combined_results, search_query, search_type
        )

        return {
            "type": "fitness_web_search_complete",
            "original_query": search_query,
            "enhanced_query": enhanced_query,
            "search_type": search_type,
            "raw_results": combined_results[:10],  # Limit raw results
            "analysis": analysis,
            "results_count": len(combined_results),
        }

    def _enhance_fitness_query(self, query: str, search_type: str) -> str:
        """Enhance search query with fitness-specific terms"""

        query_lower = query.lower()

        # Add context based on search type
        if search_type == "program":
            if "program" not in query_lower and "routine" not in query_lower:
                query += " workout program routine"

        elif search_type == "exercise":
            if "exercise" not in query_lower and "movement" not in query_lower:
                query += " exercise form technique"

        elif search_type == "research":
            query += " research study evidence science"

        # Add fitness-specific terms if not present
        fitness_terms = [
            "fitness",
            "strength",
            "muscle",
            "training",
            "workout",
            "exercise",
        ]
        if not any(term in query_lower for term in fitness_terms):
            query += " strength training fitness"

        return query

    async def _search_duckduckgo(self, query: str) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo API"""

        try:
            # Use DuckDuckGo instant answer API
            url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []

                        # Extract results from DuckDuckGo response
                        if data.get("Results"):
                            for item in data["Results"][:5]:
                                results.append({
                                    "title": item.get("Text", ""),
                                    "url": item.get("FirstURL", ""),
                                    "snippet": item.get("Result", ""),
                                    "source": "duckduckgo",
                                })

                        # Also try related topics
                        if data.get("RelatedTopics"):
                            for item in data["RelatedTopics"][:3]:
                                if isinstance(item, dict) and "Text" in item:
                                    results.append({
                                        "title": item.get("Text", "")[:100],
                                        "url": item.get("FirstURL", ""),
                                        "snippet": item.get("Text", ""),
                                        "source": "duckduckgo_related",
                                    })

                        return results

        except Exception as e:
            print(f"DuckDuckGo search failed: {e}")

        # Fallback to web scraping approach
        return await self._search_web_scraping(query)

    async def _search_web_scraping(self, query: str) -> List[Dict[str, Any]]:
        """Fallback web scraping search"""

        try:
            # Simple Google search scraping (for educational purposes)
            search_url = f"https://www.google.com/search?q={quote_plus(query)}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        results = []
                        search_results = soup.find_all("div", class_="g")

                        for result in search_results[:5]:
                            title_elem = result.find("h3")  # type: ignore
                            link_elem = result.find("a")  # type: ignore
                            snippet_elem = result.find("span", class_="aCOpRe")  # type: ignore

                            if title_elem and link_elem and hasattr(link_elem, "get"):
                                results.append({
                                    "title": title_elem.get_text()
                                    if title_elem
                                    else "",
                                    "url": link_elem.get("href", "")
                                    if link_elem
                                    else "",
                                    "snippet": (
                                        snippet_elem.get_text() if snippet_elem else ""
                                    ),
                                    "source": "web_scraping",
                                })

                        return results

        except Exception as e:
            print(f"Web scraping search failed: {e}")

        return []

    async def _search_fitness_sites(self, query: str) -> List[Dict[str, Any]]:
        """Search specific fitness websites"""

        results = []

        for site in self.fitness_sites[:3]:  # Limit to avoid rate limiting
            try:
                # Search within specific site using Google site: operator
                site_query = f"site:{site} {query}"
                site_results = await self._search_web_scraping(site_query)

                for result in site_results:
                    result["source"] = f"fitness_site_{site}"
                    results.append(result)

                # Small delay to be respectful
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"Search on {site} failed: {e}")
                continue

        return results

    async def _analyze_fitness_results(
        self, results: List[Dict], original_query: str, search_type: str
    ) -> Dict[str, Any]:
        """Analyze search results for fitness-specific insights"""

        if not results:
            return {"error": "No results to analyze"}

        # Prepare results for AI analysis
        results_text = "\n\n".join([
            f"Title: {result.get('title', '')}\nURL: {result.get('url', '')}\nSnippet: {result.get('snippet', '')}"
            for result in results[:8]  # Limit for token management
        ])

        system_prompt = """You are a fitness and exercise science expert analyzing web search results. 
        Focus on extracting actionable, evidence-based information about:
        - Workout programs and training methodologies
        - Exercise techniques and form
        - Scientific research and evidence
        - Equipment recommendations
        - Progression strategies
        
        Prioritize information from reputable fitness sources and scientific studies."""

        analysis_prompt = f"""
        Analyze these fitness-related search results for the query: "{original_query}"
        Search type: {search_type}
        
        Search Results:
        {results_text}
        
        Extract and synthesize the information in JSON format:
        {{
            "key_insights": ["main", "takeaways", "from", "results"],
            "program_recommendations": [
                {{
                    "name": "Program name if found",
                    "description": "What the program involves",
                    "source": "Which website/source",
                    "credibility": "Assessment of source credibility (1-10)",
                    "evidence_level": "Type of evidence (anecdotal, expert opinion, research-based)"
                }}
            ],
            "exercise_information": [
                {{
                    "exercise": "Exercise name",
                    "benefits": ["benefits", "listed"],
                    "form_cues": ["form", "cues", "mentioned"],
                    "equipment": "Required equipment",
                    "source": "Source website"
                }}
            ],
            "scientific_evidence": [
                {{
                    "finding": "Research finding",
                    "study_info": "Study details if mentioned",
                    "practical_application": "How to apply this"
                }}
            ],
            "equipment_recommendations": ["equipment", "mentioned", "as", "recommended"],
            "credible_sources": ["list", "of", "most", "credible", "sources"],
            "implementation_advice": "Practical advice for implementing the information",
            "further_research_needed": ["areas", "requiring", "more", "research"]
        }}
        """

        analysis_response = await self.send_message(analysis_prompt, system_prompt)

        try:
            analysis_data = json.loads(analysis_response)

            # Add metadata
            analysis_data["analysis_metadata"] = {
                "query": original_query,
                "search_type": search_type,
                "sources_analyzed": len(results),
                "analysis_model": self.model,
            }

            return analysis_data

        except json.JSONDecodeError:
            return {
                "analysis_text": analysis_response,
                "query": original_query,
                "search_type": search_type,
                "note": "Analysis in text format due to parsing error",
            }

    async def search_specific_program(self, program_name: str) -> Dict[str, Any]:
        """Search for information about a specific workout program"""

        enhanced_query = f"{program_name} workout program routine review"

        search_data = {"query": enhanced_query, "type": "program"}

        return await self.process(search_data)

    async def search_exercise_form(self, exercise_name: str) -> Dict[str, Any]:
        """Search for exercise form and technique information"""

        enhanced_query = f"{exercise_name} exercise form technique cues"

        search_data = {"query": enhanced_query, "type": "exercise"}

        return await self.process(search_data)

    async def search_fitness_research(self, topic: str) -> Dict[str, Any]:
        """Search for scientific research on fitness topics"""

        enhanced_query = f"{topic} research study evidence science pubmed"

        search_data = {"query": enhanced_query, "type": "research"}

        return await self.process(search_data)

    async def get_capabilities(self) -> List[str]:
        """Return fitness web search capabilities"""
        return [
            "program_research",
            "exercise_form_lookup",
            "scientific_literature_search",
            "equipment_research",
            "technique_analysis",
            "credibility_assessment",
        ]
