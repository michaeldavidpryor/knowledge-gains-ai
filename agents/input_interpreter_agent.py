"""
Input Interpreter Agent for analyzing and understanding user input
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
from .base_agent import BaseAgent


class InputInterpreterAgent(BaseAgent):
    """Agent specialized in interpreting user input and determining appropriate actions"""
    
    def __init__(self):
        super().__init__(name="InputInterpreterAgent", model="gpt-4", temperature=0.1)
        self.intent_categories = {
            "web_search": ["search", "find", "lookup", "research", "investigate", "google", "web"],
            "file_search": ["file", "code", "document", "local", "project", "repository", "folder"],
            "analysis": ["analyze", "summarize", "explain", "interpret", "understand", "breakdown"],
            "information": ["what", "how", "why", "when", "where", "who", "tell me about"],
            "comparison": ["compare", "difference", "vs", "versus", "contrast", "similar"],
            "help": ["help", "assist", "guide", "support", "tutorial", "how to"]
        }
        
    async def process(self, input_data: Any) -> Dict[str, Any]:
        """Process and interpret user input"""
        if isinstance(input_data, str):
            user_input = input_data
        elif isinstance(input_data, dict) and "input" in input_data:
            user_input = input_data["input"]
        else:
            return {"error": "Invalid input format for interpretation"}
            
        if not user_input.strip():
            return {"error": "Empty input provided"}
            
        # Perform comprehensive input analysis
        interpretation = await self.interpret_input(user_input)
        
        return interpretation
    
    async def interpret_input(self, user_input: str) -> Dict[str, Any]:
        """Interpret user input and determine intent, entities, and required actions"""
        
        system_prompt = """You are an expert input interpreter for an AI agent system. Your job is to analyze user input and determine:

1. Primary Intent: The main action the user wants to perform
2. Secondary Intent: Any additional or related actions
3. Entities: Key information, topics, or subjects mentioned
4. Scope: Whether the request is local (files) or external (web search)
5. Urgency: How time-sensitive the request is
6. Complexity: How complex the request is
7. Required Agents: Which agents should handle this request
8. Context: Any additional context or background information

Respond with a structured JSON format containing these analysis points."""

        analysis_prompt = f"""
        Analyze this user input: "{user_input}"
        
        Please provide a comprehensive interpretation in the following JSON format:
        {{
            "primary_intent": "main action user wants",
            "secondary_intent": "additional actions if any",
            "entities": ["key", "topics", "mentioned"],
            "scope": "local|web|both",
            "urgency": "low|medium|high",
            "complexity": "simple|moderate|complex",
            "confidence": 0.95,
            "suggested_agents": ["agent1", "agent2"],
            "search_queries": ["refined query 1", "refined query 2"],
            "context": "additional context or background",
            "requires_clarification": false,
            "clarification_questions": []
        }}
        
        Make sure to extract the most relevant search terms and suggest the most appropriate agents.
        """
        
        interpretation_response = await self.send_message(analysis_prompt, system_prompt)
        
        # Parse the JSON response
        try:
            interpretation = json.loads(interpretation_response)
        except json.JSONDecodeError:
            # Fallback to basic interpretation if JSON parsing fails
            interpretation = await self._fallback_interpretation(user_input)
        
        # Add basic keyword analysis
        interpretation["keyword_analysis"] = self._analyze_keywords(user_input)
        
        # Enhance with agent recommendations
        interpretation["agent_recommendations"] = self._recommend_agents(interpretation)
        
        return interpretation
    
    async def _fallback_interpretation(self, user_input: str) -> Dict[str, Any]:
        """Fallback interpretation method if JSON parsing fails"""
        keywords = self._analyze_keywords(user_input)
        
        # Determine primary intent based on keywords
        primary_intent = "information"
        scope = "both"
        
        if any(keyword in keywords["web_indicators"] for keyword in user_input.lower().split()):
            scope = "web"
            primary_intent = "web_search"
        elif any(keyword in keywords["file_indicators"] for keyword in user_input.lower().split()):
            scope = "local"
            primary_intent = "file_search"
            
        return {
            "primary_intent": primary_intent,
            "secondary_intent": "",
            "entities": user_input.split(),
            "scope": scope,
            "urgency": "medium",
            "complexity": "moderate",
            "confidence": 0.7,
            "suggested_agents": self._suggest_agents_by_scope(scope),
            "search_queries": [user_input],
            "context": "Fallback interpretation due to parsing error",
            "requires_clarification": False,
            "clarification_questions": [],
            "keyword_analysis": keywords
        }
    
    def _analyze_keywords(self, user_input: str) -> Dict[str, List[str]]:
        """Analyze keywords to determine intent indicators"""
        words = user_input.lower().split()
        
        analysis = {
            "web_indicators": [],
            "file_indicators": [],
            "action_words": [],
            "question_words": [],
            "entities": []
        }
        
        # Check for web search indicators
        web_keywords = ["search", "google", "find online", "web", "internet", "latest", "news", "current"]
        analysis["web_indicators"] = [word for word in words if any(keyword in word for keyword in web_keywords)]
        
        # Check for file search indicators
        file_keywords = ["file", "code", "project", "local", "repository", "folder", "document"]
        analysis["file_indicators"] = [word for word in words if any(keyword in word for keyword in file_keywords)]
        
        # Check for action words
        action_keywords = ["find", "search", "analyze", "explain", "compare", "help", "show", "tell"]
        analysis["action_words"] = [word for word in words if word in action_keywords]
        
        # Check for question words
        question_keywords = ["what", "how", "why", "when", "where", "who", "which"]
        analysis["question_words"] = [word for word in words if word in question_keywords]
        
        # Extract potential entities (nouns, proper nouns)
        analysis["entities"] = [word for word in words if len(word) > 3 and word.isalpha()]
        
        return analysis
    
    def _recommend_agents(self, interpretation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Recommend agents based on interpretation"""
        recommendations = []
        
        scope = interpretation.get("scope", "both")
        primary_intent = interpretation.get("primary_intent", "")
        
        if scope in ["web", "both"]:
            recommendations.append({
                "agent": "WebSearchAgent",
                "priority": "high" if scope == "web" else "medium",
                "reason": "User request involves external information search"
            })
        
        if scope in ["local", "both"]:
            recommendations.append({
                "agent": "FileSearchAgent", 
                "priority": "high" if scope == "local" else "medium",
                "reason": "User request involves local file or code search"
            })
            
        # Always recommend handoff agent for coordination
        recommendations.append({
            "agent": "HandoffAgent",
            "priority": "high",
            "reason": "Coordinate workflow between multiple agents"
        })
        
        return recommendations
    
    def _suggest_agents_by_scope(self, scope: str) -> List[str]:
        """Suggest agents based on scope"""
        if scope == "web":
            return ["WebSearchAgent", "HandoffAgent"]
        elif scope == "local":
            return ["FileSearchAgent", "HandoffAgent"]
        else:
            return ["WebSearchAgent", "FileSearchAgent", "HandoffAgent"]
    
    async def refine_query(self, original_query: str, context: Dict[str, Any]) -> str:
        """Refine a query based on context and previous interactions"""
        system_prompt = """You are a query refinement specialist. Take the original user query and context to create a more specific, targeted search query that will yield better results."""
        
        refinement_prompt = f"""
        Original Query: {original_query}
        Context: {json.dumps(context, indent=2)}
        
        Please provide a refined, more specific query that would yield better search results. Focus on:
        1. Key terms and concepts
        2. Removing ambiguity
        3. Adding relevant context
        4. Making it more searchable
        
        Return only the refined query, nothing else.
        """
        
        refined_query = await self.send_message(refinement_prompt, system_prompt)
        return refined_query.strip()
    
    async def get_capabilities(self) -> List[str]:
        """Return input interpretation capabilities"""
        return [
            "intent_recognition",
            "entity_extraction", 
            "scope_determination",
            "agent_recommendation",
            "query_refinement",
            "context_analysis"
        ]