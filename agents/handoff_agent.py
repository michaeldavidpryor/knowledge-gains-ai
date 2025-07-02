"""
Handoff Agent for coordinating workflow between different agents
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple
from .base_agent import BaseAgent


class HandoffAgent(BaseAgent):
    """Agent specialized in coordinating workflow and managing handoffs between agents"""
    
    def __init__(self):
        super().__init__(name="HandoffAgent", model="gpt-4", temperature=0.2)
        self.agent_registry = {}
        self.workflow_history = []
        self.active_workflows = {}
        
    def register_agent(self, agent_name: str, agent_instance):
        """Register an agent for coordination"""
        self.agent_registry[agent_name] = agent_instance
        
    async def process(self, input_data: Any) -> Dict[str, Any]:
        """Process coordination request and manage workflow"""
        if isinstance(input_data, dict):
            workflow_request = input_data
        else:
            return {"error": "Invalid workflow request format"}
            
        workflow_id = workflow_request.get("workflow_id", f"workflow_{len(self.workflow_history)}")
        
        # Execute workflow coordination
        result = await self.coordinate_workflow(workflow_request, workflow_id)
        
        # Store workflow history
        self.workflow_history.append({
            "workflow_id": workflow_id,
            "request": workflow_request,
            "result": result,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        return result
    
    async def coordinate_workflow(self, workflow_request: Dict[str, Any], workflow_id: str) -> Dict[str, Any]:
        """Coordinate the execution of multiple agents based on workflow request"""
        
        # Extract workflow parameters
        user_query = workflow_request.get("user_query", "")
        interpretation = workflow_request.get("interpretation", {})
        suggested_agents = interpretation.get("suggested_agents", [])
        scope = interpretation.get("scope", "both")
        
        if not user_query:
            return {"error": "No user query provided for workflow coordination"}
            
        # Plan the workflow execution
        execution_plan = await self.plan_workflow(interpretation, suggested_agents, scope)
        
        # Execute the planned workflow
        workflow_results = await self.execute_workflow_plan(execution_plan, user_query, workflow_id)
        
        # Synthesize final response
        final_response = await self.synthesize_response(workflow_results, user_query, interpretation)
        
        return {
            "workflow_id": workflow_id,
            "user_query": user_query,
            "execution_plan": execution_plan,
            "agent_results": workflow_results,
            "final_response": final_response,
            "status": "completed"
        }
    
    async def plan_workflow(self, interpretation: Dict[str, Any], suggested_agents: List[str], scope: str) -> Dict[str, Any]:
        """Plan the workflow execution strategy"""
        
        system_prompt = """You are a workflow planning specialist. Given user intent interpretation and available agents, create an optimal execution plan.
        
        Available agents:
        - WebSearchAgent: Searches the internet for information
        - FileSearchAgent: Searches local files and documents  
        - InputInterpreterAgent: Interprets and analyzes user input
        - HandoffAgent: Coordinates workflow between agents
        
        Plan should include: agent sequence, parallel execution opportunities, dependencies, and coordination strategy."""
        
        planning_prompt = f"""
        User Intent Analysis: {json.dumps(interpretation, indent=2)}
        Suggested Agents: {suggested_agents}
        Scope: {scope}
        
        Create an execution plan in the following JSON format:
        {{
            "execution_strategy": "sequential|parallel|hybrid",
            "agent_sequence": [
                {{
                    "agent": "AgentName",
                    "priority": "high|medium|low", 
                    "input_type": "original_query|refined_query|previous_results",
                    "dependencies": ["agent1", "agent2"],
                    "parallel_group": 1
                }}
            ],
            "coordination_strategy": "merge_results|prioritize_best|sequential_refinement",
            "estimated_duration": "short|medium|long",
            "confidence": 0.95
        }}
        """
        
        plan_response = await self.send_message(planning_prompt, system_prompt)
        
        try:
            execution_plan = json.loads(plan_response)
        except json.JSONDecodeError:
            # Fallback plan
            execution_plan = self._create_fallback_plan(suggested_agents, scope)
            
        return execution_plan
    
    async def execute_workflow_plan(self, execution_plan: Dict[str, Any], user_query: str, workflow_id: str) -> Dict[str, Any]:
        """Execute the planned workflow with the registered agents"""
        
        strategy = execution_plan.get("execution_strategy", "sequential")
        agent_sequence = execution_plan.get("agent_sequence", [])
        
        self.active_workflows[workflow_id] = {
            "status": "executing",
            "current_step": 0,
            "total_steps": len(agent_sequence),
            "results": {}
        }
        
        workflow_results = {}
        
        if strategy == "parallel":
            workflow_results = await self._execute_parallel(agent_sequence, user_query, workflow_id)
        elif strategy == "sequential":
            workflow_results = await self._execute_sequential(agent_sequence, user_query, workflow_id)
        else:  # hybrid
            workflow_results = await self._execute_hybrid(agent_sequence, user_query, workflow_id)
            
        self.active_workflows[workflow_id]["status"] = "completed"
        return workflow_results
    
    async def _execute_parallel(self, agent_sequence: List[Dict], user_query: str, workflow_id: str) -> Dict[str, Any]:
        """Execute agents in parallel"""
        tasks = []
        results = {}
        
        for agent_config in agent_sequence:
            agent_name = agent_config.get("agent")
            if agent_name in self.agent_registry:
                agent = self.agent_registry[agent_name]
                task = asyncio.create_task(
                    self._execute_single_agent(agent, agent_config, user_query, workflow_id)
                )
                tasks.append((agent_name, task))
        
        # Wait for all tasks to complete
        for agent_name, task in tasks:
            try:
                result = await task
                results[agent_name] = result
            except Exception as e:
                results[agent_name] = {"error": str(e)}
                
        return results
    
    async def _execute_sequential(self, agent_sequence: List[Dict], user_query: str, workflow_id: str) -> Dict[str, Any]:
        """Execute agents sequentially"""
        results = {}
        context = {"original_query": user_query}
        
        for i, agent_config in enumerate(agent_sequence):
            agent_name = agent_config.get("agent")
            
            if agent_name in self.agent_registry:
                self.active_workflows[workflow_id]["current_step"] = i + 1
                
                agent = self.agent_registry[agent_name]
                
                # Prepare input based on dependencies and input type
                agent_input = self._prepare_agent_input(agent_config, user_query, results, context)
                
                try:
                    result = await agent.process(agent_input)
                    results[agent_name] = result
                    context[agent_name] = result
                except Exception as e:
                    results[agent_name] = {"error": str(e)}
                    
        return results
    
    async def _execute_hybrid(self, agent_sequence: List[Dict], user_query: str, workflow_id: str) -> Dict[str, Any]:
        """Execute agents using hybrid strategy (grouping parallel where possible)"""
        results = {}
        
        # Group agents by parallel_group
        groups = {}
        for agent_config in agent_sequence:
            group_id = agent_config.get("parallel_group", 1)
            group_key = str(group_id)
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(agent_config)
        
        # Execute groups sequentially, agents within groups in parallel
        for group_key in sorted(groups.keys()):
            group_agents = groups[group_key]
            
            if len(group_agents) == 1:
                # Single agent execution
                agent_config = group_agents[0]
                agent_name = agent_config.get("agent")
                
                if agent_name in self.agent_registry:
                    agent = self.agent_registry[agent_name]
                    agent_input = self._prepare_agent_input(agent_config, user_query, results, {})
                    
                    try:
                        result = await agent.process(agent_input)
                        results[agent_name] = result
                    except Exception as e:
                        results[agent_name] = {"error": str(e)}
            else:
                # Parallel execution within group
                tasks = []
                for agent_config in group_agents:
                    agent_name = agent_config.get("agent")
                    if agent_name in self.agent_registry:
                        agent = self.agent_registry[agent_name]
                        agent_input = self._prepare_agent_input(agent_config, user_query, results, {})
                        task = asyncio.create_task(agent.process(agent_input))
                        tasks.append((agent_name, task))
                
                # Wait for group to complete
                for agent_name, task in tasks:
                    try:
                        result = await task
                        results[agent_name] = result
                    except Exception as e:
                        results[agent_name] = {"error": str(e)}
                        
        return results
    
    async def _execute_single_agent(self, agent, agent_config: Dict, user_query: str, workflow_id: str) -> Dict[str, Any]:
        """Execute a single agent"""
        agent_input = self._prepare_agent_input(agent_config, user_query, {}, {})
        return await agent.process(agent_input)
    
    def _prepare_agent_input(self, agent_config: Dict, user_query: str, previous_results: Dict, context: Dict) -> Any:
        """Prepare input for an agent based on its configuration"""
        input_type = agent_config.get("input_type", "original_query")
        
        if input_type == "original_query":
            return user_query
        elif input_type == "refined_query" and "InputInterpreterAgent" in previous_results:
            interpreter_result = previous_results["InputInterpreterAgent"]
            refined_queries = interpreter_result.get("search_queries", [user_query])
            return refined_queries[0] if refined_queries else user_query
        elif input_type == "previous_results":
            return {
                "query": user_query,
                "context": previous_results,
                "additional_context": context
            }
        else:
            return user_query
    
    def _create_fallback_plan(self, suggested_agents: List[str], scope: str) -> Dict[str, Any]:
        """Create a fallback execution plan"""
        agent_sequence = []
        
        # Add input interpreter first
        if "InputInterpreterAgent" not in suggested_agents:
            agent_sequence.append({
                "agent": "InputInterpreterAgent",
                "priority": "high",
                "input_type": "original_query", 
                "dependencies": [],
                "parallel_group": 1
            })
        
        # Add search agents based on scope
        parallel_group = 2
        if scope in ["web", "both"] and "WebSearchAgent" in self.agent_registry:
            agent_sequence.append({
                "agent": "WebSearchAgent",
                "priority": "high",
                "input_type": "refined_query",
                "dependencies": ["InputInterpreterAgent"],
                "parallel_group": parallel_group
            })
            
        if scope in ["local", "both"] and "FileSearchAgent" in self.agent_registry:
            agent_sequence.append({
                "agent": "FileSearchAgent", 
                "priority": "high",
                "input_type": "refined_query",
                "dependencies": ["InputInterpreterAgent"],
                "parallel_group": parallel_group
            })
        
        return {
            "execution_strategy": "sequential",
            "agent_sequence": agent_sequence,
            "coordination_strategy": "merge_results",
            "estimated_duration": "medium",
            "confidence": 0.8
        }
    
    async def synthesize_response(self, workflow_results: Dict[str, Any], user_query: str, interpretation: Dict[str, Any]) -> str:
        """Synthesize final response from all agent results"""
        
        system_prompt = """You are a response synthesis specialist. Combine results from multiple AI agents into a comprehensive, coherent response for the user.
        
        Focus on:
        1. Answering the user's original question
        2. Integrating information from all sources
        3. Highlighting the most relevant findings
        4. Providing clear, actionable insights
        5. Maintaining consistency and avoiding contradictions"""
        
        synthesis_prompt = f"""
        Original User Query: {user_query}
        User Intent: {interpretation.get('primary_intent', 'information')}
        
        Agent Results:
        {json.dumps(workflow_results, indent=2)}
        
        Please synthesize these results into a comprehensive response that directly addresses the user's query. 
        Organize the information clearly and highlight the most important findings.
        """
        
        synthesized_response = await self.send_message(synthesis_prompt, system_prompt)
        
        return synthesized_response
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get the status of an active workflow"""
        if workflow_id in self.active_workflows:
            return self.active_workflows[workflow_id]
        
        # Check workflow history
        for workflow in self.workflow_history:
            if workflow["workflow_id"] == workflow_id:
                return {"status": "completed", "result": workflow["result"]}
                
        return {"status": "not_found"}
    
    async def get_capabilities(self) -> List[str]:
        """Return handoff coordination capabilities"""
        return [
            "workflow_coordination",
            "agent_orchestration",
            "parallel_execution", 
            "sequential_execution",
            "result_synthesis",
            "dependency_management"
        ]