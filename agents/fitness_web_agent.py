"""
Fitness Web Agent for searching and analyzing fitness information
Using OpenAI Assistants API with function calling for web search
"""

import json
from typing import Any, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

from .base_agent import BaseAgent


class FitnessWebAgent(BaseAgent):
    """Specialized web search agent for fitness information using Assistants API"""

    def __init__(self):
        super().__init__(name="FitnessWebAgent", model="gpt-4.1-2025-04-14", temperature=0.3)
        self.search_engines = {
            "duckduckgo": self._search_duckduckgo,
            "fitness_sites": self._search_fitness_sites,
        }
        self.fitness_sites = [
            "strongerbyscience.com",
            "barbellmedicine.com", 
            "t-nation.com",
            "bodybuilding.com",
            "ncbi.nlm.nih.gov",
            "pubmed.ncbi.nlm.nih.gov",
        ]

    async def initialize(self):
        """Initialize the assistant with web search capabilities"""
        instructions = """You are an expert fitness and exercise science researcher specializing in:
        - Strength training and powerlifting programming
        - Exercise biomechanics and technique
        - Sports nutrition and supplementation
        - Recovery and injury prevention
        - Scientific literature analysis
        
        When searching for information:
        1. Prioritize peer-reviewed scientific studies
        2. Look for evidence-based recommendations
        3. Consider the source credibility
        4. Extract practical applications
        5. Synthesize multiple sources for comprehensive answers
        
        You can search the web using function calls to find the most up-to-date and accurate information."""
        
        # Note: Web search will be implemented via function calling
        await self.initialize_assistant(
            instructions=instructions,
            tools=[]  # No built-in tools, we'll use function calling
        )

    async def process(self, input_data: Any) -> Dict[str, Any]:
        """Process fitness-related web search requests"""
        
        # Initialize assistant if not already done
        if not self.assistant_id:
            await self.initialize()
        
        if isinstance(input_data, str):
            query = input_data
            search_type = "general"
        elif isinstance(input_data, dict):
            query = input_data.get("query", "")
            search_type = input_data.get("search_type", "general")
        else:
            return {
                "type": "error",
                "message": "Invalid input format",
                "expected": "String query or dictionary with 'query' key"
            }

        # Perform search based on type
        if search_type == "scientific":
            return await self._search_scientific_literature(query)
        elif search_type == "technique":
            return await self._search_exercise_technique(query)
        elif search_type == "program":
            return await self._search_workout_programs(query)
        else:
            return await self._general_fitness_search(query)

    async def _general_fitness_search(self, query: str) -> Dict[str, Any]:
        """Perform general fitness-related web search"""
        
        # Search using multiple sources
        search_results = await self._perform_web_search(query)
        
        if not search_results:
            return {
                "type": "search_error", 
                "message": "No search results found",
                "query": query
            }
        
        # Analyze results with AI
        analysis_prompt = f"""Analyze these web search results for: "{query}"
        
        Search Results:
        {json.dumps(search_results[:5], indent=2)}
        
        Provide:
        1. Key findings and recommendations
        2. Scientific evidence (if any)
        3. Practical applications
        4. Source credibility assessment
        5. Additional considerations
        
        Format as a comprehensive yet concise response."""
        
        response = await self.send_message(analysis_prompt)
        
        return {
            "type": "web_search_complete",
            "query": query,
            "analysis": response,
            "sources": search_results[:5],
            "search_type": "general"
        }

    async def _search_scientific_literature(self, query: str) -> Dict[str, Any]:
        """Search for scientific studies and research"""
        
        # Add scientific search terms
        scientific_query = f"{query} site:pubmed.ncbi.nlm.nih.gov OR site:ncbi.nlm.nih.gov OR systematic review OR meta-analysis"
        
        search_results = await self._perform_web_search(scientific_query)
        
        # Filter for scientific sources
        scientific_results = [
            result for result in search_results
            if any(domain in result.get("url", "") for domain in ["ncbi.nlm.nih.gov", "pubmed"])
        ]
        
        analysis_prompt = f"""Analyze scientific literature for: "{query}"
        
        Scientific Sources Found:
        {json.dumps(scientific_results[:5], indent=2)}
        
        Provide:
        1. Research summary with key findings
        2. Study quality and limitations
        3. Practical implications for training
        4. Areas needing more research
        5. Evidence-based recommendations
        
        Focus on translating research into practical applications."""
        
        response = await self.send_message(analysis_prompt)
        
        return {
            "type": "scientific_search_complete",
            "query": query,
            "analysis": response,
            "scientific_sources": scientific_results[:5],
            "total_studies_found": len(scientific_results)
        }

    async def _search_exercise_technique(self, exercise_name: str) -> Dict[str, Any]:
        """Search for exercise technique and form information"""
        
        technique_query = f"{exercise_name} proper form technique cues common mistakes"
        
        search_results = await self._perform_web_search(technique_query)
        
        # Prioritize reputable fitness sites
        technique_results = self._prioritize_fitness_sites(search_results)
        
        analysis_prompt = f"""Analyze exercise technique for: "{exercise_name}"
        
        Technique Resources:
        {json.dumps(technique_results[:5], indent=2)}
        
        Provide comprehensive technique guide:
        1. Setup and starting position
        2. Movement execution (step-by-step)
        3. Common form errors and fixes
        4. Safety considerations
        5. Muscle activation and biomechanics
        6. Variations for different goals/limitations
        7. Programming recommendations
        
        Be specific and practical."""
        
        response = await self.send_message(analysis_prompt)
        
        return {
            "type": "technique_analysis_complete",
            "exercise": exercise_name,
            "analysis": response,
            "sources": technique_results[:5]
        }

    async def _search_workout_programs(self, program_type: str) -> Dict[str, Any]:
        """Search for workout programs and templates"""
        
        program_query = f"{program_type} workout program template sets reps"
        
        search_results = await self._perform_web_search(program_query)
        
        # Filter for program-related content
        program_results = self._prioritize_fitness_sites(search_results)
        
        analysis_prompt = f"""Find and analyze workout programs for: "{program_type}"
        
        Program Resources:
        {json.dumps(program_results[:5], indent=2)}
        
        Extract and synthesize:
        1. Program structure and periodization
        2. Exercise selection and order
        3. Volume and intensity parameters
        4. Progression schemes
        5. Recovery and deload protocols
        6. Equipment requirements
        7. Who the program is best suited for
        
        Provide practical program recommendations."""
        
        response = await self.send_message(analysis_prompt)
        
        return {
            "type": "program_search_complete",
            "program_type": program_type,
            "analysis": response,
            "sources": program_results[:5]
        }

    async def _perform_web_search(self, query: str) -> List[Dict[str, Any]]:
        """Perform actual web search using available engines"""
        
        # Try primary search engine
        results = await self._search_duckduckgo(query)
        
        if not results:
            # Fallback to fitness site search
            results = await self._search_fitness_sites(query)
        
        return results

    async def _search_duckduckgo(self, query: str) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo API"""
        
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        results = []
                        
                        # Extract results from DuckDuckGo response
                        if data.get("RelatedTopics"):
                            for topic in data["RelatedTopics"][:10]:
                                if isinstance(topic, dict) and "Text" in topic:
                                    results.append({
                                        "title": topic.get("Text", "")[:100],
                                        "url": topic.get("FirstURL", ""),
                                        "snippet": topic.get("Text", "")
                                    })
                        
                        return results
                        
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
            
        return []

    async def _search_fitness_sites(self, query: str) -> List[Dict[str, Any]]:
        """Search specific fitness websites"""
        
        results = []
        
        # Create Google site-specific search query
        site_query = " OR ".join([f"site:{site}" for site in self.fitness_sites])
        search_url = f"https://www.google.com/search?q={query} {site_query}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Extract search results (simplified)
                        for result in soup.find_all('div', class_='g')[:10]:
                            title_elem = result.find('h3')
                            link_elem = result.find('a')
                            snippet_elem = result.find('span', class_='st')
                            
                            if title_elem and link_elem:
                                results.append({
                                    "title": title_elem.get_text(),
                                    "url": link_elem.get('href', ''),
                                    "snippet": snippet_elem.get_text() if snippet_elem else ""
                                })
                                
        except Exception as e:
            print(f"Fitness site search error: {e}")
            
        return results

    def _prioritize_fitness_sites(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize results from known reputable fitness sites"""
        
        prioritized = []
        other = []
        
        for result in results:
            url = result.get("url", "")
            if any(site in url for site in self.fitness_sites):
                prioritized.append(result)
            else:
                other.append(result)
        
        # Return prioritized results first, then others
        return prioritized + other

    async def research_topic(self, topic: str, depth: str = "moderate") -> Dict[str, Any]:
        """Conduct in-depth research on a fitness topic"""
        
        if not self.assistant_id:
            await self.initialize()
        
        # Determine search queries based on depth
        if depth == "comprehensive":
            queries = [
                f"{topic} scientific research studies",
                f"{topic} systematic review meta-analysis", 
                f"{topic} practical application training",
                f"{topic} common mistakes myths"
            ]
        else:
            queries = [
                f"{topic} evidence-based recommendations",
                f"{topic} best practices"
            ]
        
        # Perform multiple searches
        all_results = []
        for query in queries:
            results = await self._perform_web_search(query)
            all_results.extend(results)
        
        # Remove duplicates based on URL
        unique_results = []
        seen_urls = set()
        for result in all_results:
            url = result.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        # Comprehensive analysis
        research_prompt = f"""Conduct {depth} research on: "{topic}"
        
        Research Sources ({len(unique_results)} unique sources):
        {json.dumps(unique_results[:15], indent=2)}
        
        Create a comprehensive research summary including:
        
        1. **Current Scientific Understanding**
           - Key research findings
           - Consensus vs. controversial areas
           
        2. **Practical Applications**
           - Evidence-based recommendations
           - Implementation strategies
           
        3. **Common Misconceptions**
           - Myths to avoid
           - Why they persist
           
        4. **Programming Considerations**
           - How to apply this knowledge
           - Individual variations
           
        5. **Future Directions**
           - Gaps in current knowledge
           - Emerging research
           
        Cite sources where appropriate."""
        
        response = await self.send_message(research_prompt)
        
        return {
            "type": "research_complete",
            "topic": topic,
            "depth": depth,
            "research_summary": response,
            "sources_analyzed": len(unique_results),
            "key_sources": unique_results[:10]
        }

    async def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities"""
        base_capabilities = await super().get_capabilities()
        return base_capabilities + [
            "web_search",
            "scientific_literature_search",
            "exercise_technique_research", 
            "program_discovery",
            "evidence_synthesis",
            "source_credibility_assessment"
        ]
