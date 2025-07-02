"""
Web Search Service for fitness and exercise information
Using OpenAI Responses API with web search capabilities
"""

import json
from typing import Any, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

from .base_service import BaseService


class WebSearchService(BaseService):
    """Service for web search and fitness information retrieval using Responses API"""

    def __init__(self):
        super().__init__(name="WebSearchService", model="gpt-4.1-2025-04-14", temperature=0.3)
        # Initialize with web_search tool
        self.tools = [{"type": "web_search"}]
        self.fitness_sites = [
            "strongerbyscience.com",
            "barbellmedicine.com", 
            "t-nation.com",
            "bodybuilding.com",
            "ncbi.nlm.nih.gov",
            "pubmed.ncbi.nlm.nih.gov",
        ]

    async def process(self, input_data: Any) -> Dict[str, Any]:
        """Process fitness-related web search requests"""
        
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
        """Perform general fitness-related web search using built-in web_search tool"""
        
        # Use the Responses API web_search tool
        search_prompt = f"""Search for information about: "{query}"
        
        Focus on:
        1. Evidence-based fitness and exercise information
        2. Scientific studies and research
        3. Practical applications for training
        4. Safety and best practices
        
        Provide a comprehensive summary of findings with sources."""
        
        # The web_search tool is automatically invoked by the model
        response = await self.send_message(search_prompt)
        
        return {
            "type": "web_search_complete",
            "query": query,
            "analysis": response,
            "search_type": "general"
        }

    async def _search_scientific_literature(self, query: str) -> Dict[str, Any]:
        """Search for scientific studies and research"""
        
        scientific_prompt = f"""Search for scientific literature about: "{query}"
        
        Focus specifically on:
        1. Peer-reviewed research studies
        2. Meta-analyses and systematic reviews
        3. Studies from PubMed, NCBI, or academic journals
        4. Evidence quality and study limitations
        5. Practical implications for training
        
        Prioritize recent research and provide evidence-based recommendations."""
        
        response = await self.send_message(scientific_prompt)
        
        return {
            "type": "scientific_search_complete",
            "query": query,
            "analysis": response,
            "search_type": "scientific"
        }

    async def _search_exercise_technique(self, exercise_name: str) -> Dict[str, Any]:
        """Search for exercise technique and form information"""
        
        technique_prompt = f"""Search for detailed information about proper form and technique for: "{exercise_name}"
        
        Find and summarize:
        1. Setup and starting position
        2. Step-by-step movement execution
        3. Common form errors and how to fix them
        4. Safety considerations and injury prevention
        5. Muscle activation and biomechanics
        6. Variations for different goals or limitations
        7. Programming recommendations
        
        Focus on evidence-based sources and expert guidance."""
        
        response = await self.send_message(technique_prompt)
        
        return {
            "type": "technique_analysis_complete",
            "exercise": exercise_name,
            "analysis": response,
            "search_type": "technique"
        }

    async def _search_workout_programs(self, program_type: str) -> Dict[str, Any]:
        """Search for workout programs and templates"""
        
        program_prompt = f"""Search for workout programs and templates for: "{program_type}"
        
        Find and analyze:
        1. Program structure and periodization
        2. Exercise selection and order
        3. Volume and intensity parameters
        4. Progression schemes
        5. Recovery and deload protocols
        6. Equipment requirements
        7. Who the program is best suited for
        
        Provide practical program recommendations from reputable sources."""
        
        response = await self.send_message(program_prompt)
        
        return {
            "type": "program_search_complete",
            "program_type": program_type,
            "analysis": response,
            "search_type": "program"
        }

    async def research_topic(self, topic: str, depth: str = "moderate") -> Dict[str, Any]:
        """Conduct in-depth research on a fitness topic"""
        
        depth_instructions = {
            "basic": "Provide a concise overview with key points",
            "moderate": "Provide a thorough analysis with multiple perspectives",
            "comprehensive": "Provide an exhaustive analysis including controversies and emerging research"
        }
        
        research_prompt = f"""Conduct {depth} research on the fitness/exercise topic: "{topic}"
        
        {depth_instructions.get(depth, depth_instructions["moderate"])}
        
        Structure your research to include:
        
        1. **Current Scientific Understanding**
           - Key research findings
           - Areas of consensus vs. controversy
           
        2. **Practical Applications**
           - Evidence-based recommendations
           - Implementation strategies
           
        3. **Common Misconceptions**
           - Myths to avoid
           - Why they persist
           
        4. **Programming Considerations**
           - How to apply this knowledge
           - Individual variations to consider
           
        5. **Future Directions**
           - Gaps in current knowledge
           - Emerging research areas
           
        Use web search to find the most current and reliable information."""
        
        response = await self.send_message(research_prompt)
        
        return {
            "type": "research_complete",
            "topic": topic,
            "depth": depth,
            "research_summary": response
        }

    async def compare_programs(self, program1: str, program2: str) -> Dict[str, Any]:
        """Compare two workout programs"""
        
        comparison_prompt = f"""Compare and contrast these two workout programs: "{program1}" vs "{program2}"
        
        Analyze:
        1. Training philosophy and principles
        2. Volume and intensity differences
        3. Exercise selection
        4. Progression methods
        5. Target audience
        6. Pros and cons of each
        7. Which to choose based on different goals
        
        Search for information about both programs and provide an objective comparison."""
        
        response = await self.send_message(comparison_prompt)
        
        return {
            "type": "program_comparison",
            "program1": program1,
            "program2": program2,
            "comparison": response
        }

    async def verify_information(self, claim: str) -> Dict[str, Any]:
        """Fact-check fitness claims"""
        
        verify_prompt = f"""Verify this fitness/exercise claim: "{claim}"
        
        Search for:
        1. Scientific evidence supporting or refuting the claim
        2. Expert opinions and consensus
        3. Quality of available evidence
        4. Context and nuance
        5. Common misunderstandings
        
        Provide a fact-based assessment of the claim's validity."""
        
        response = await self.send_message(verify_prompt)
        
        return {
            "type": "fact_check",
            "claim": claim,
            "verification": response
        }

    async def get_capabilities(self) -> List[str]:
        """Return list of service capabilities"""
        base_capabilities = await super().get_capabilities()
        return base_capabilities + [
            "web_search",
            "scientific_literature_search",
            "exercise_technique_research", 
            "program_discovery",
            "evidence_synthesis",
            "fact_checking",
            "program_comparison"
        ]