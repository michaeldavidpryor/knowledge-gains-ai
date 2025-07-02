"""
Workflow Coordinator - Main orchestrator for the OpenAI Agentic Workflow System
"""

import asyncio
import os
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .input_interpreter_agent import InputInterpreterAgent
from .web_search_agent import WebSearchAgent
from .file_search_agent import FileSearchAgent
from .handoff_agent import HandoffAgent


class WorkflowCoordinator:
    """Main coordinator that orchestrates the entire agentic workflow"""
    
    def __init__(self, search_directories: Optional[List[str]] = None):
        self.console = Console()
        
        # Initialize all agents
        self.input_interpreter = InputInterpreterAgent()
        self.web_search_agent = WebSearchAgent()
        self.file_search_agent = FileSearchAgent(search_directories)
        self.handoff_agent = HandoffAgent()
        
        # Register agents with handoff coordinator
        self._register_agents()
        
        # Workflow tracking
        self.session_history = []
        self.current_workflow_id = None
        
    def _register_agents(self):
        """Register all agents with the handoff coordinator"""
        self.handoff_agent.register_agent("InputInterpreterAgent", self.input_interpreter)
        self.handoff_agent.register_agent("WebSearchAgent", self.web_search_agent)
        self.handoff_agent.register_agent("FileSearchAgent", self.file_search_agent)
        self.handoff_agent.register_agent("HandoffAgent", self.handoff_agent)
        
    async def process_query(self, user_query: str, workflow_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a user query through the complete agentic workflow"""
        
        if not user_query.strip():
            return {"error": "Empty query provided"}
            
        self.console.print(f"\n🚀 Processing query: [bold cyan]{user_query}[/bold cyan]")
        
        try:
            # Step 1: Interpret user input
            self.console.print("\n📝 [bold yellow]Step 1:[/bold yellow] Interpreting user input...")
            interpretation = await self.input_interpreter.process(user_query)
            
            if "error" in interpretation:
                return interpretation
                
            self._display_interpretation(interpretation)
            
            # Step 2: Plan and execute workflow
            self.console.print("\n🔄 [bold yellow]Step 2:[/bold yellow] Planning and executing workflow...")
            
            workflow_request = {
                "user_query": user_query,
                "interpretation": interpretation,
                "options": workflow_options or {}
            }
            
            # Execute coordinated workflow
            workflow_result = await self.handoff_agent.process(workflow_request)
            
            # Step 3: Present results
            self.console.print("\n✅ [bold yellow]Step 3:[/bold yellow] Presenting results...")
            self._display_results(workflow_result)
            
            # Store in session history
            session_entry = {
                "query": user_query,
                "interpretation": interpretation,
                "workflow_result": workflow_result,
                "timestamp": asyncio.get_event_loop().time()
            }
            self.session_history.append(session_entry)
            
            return workflow_result
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            self.console.print(f"\n❌ [bold red]{error_msg}[/bold red]")
            return {"error": error_msg}
    
    def _display_interpretation(self, interpretation: Dict[str, Any]):
        """Display the input interpretation results"""
        
        table = Table(title="🧠 Input Interpretation", show_header=True, header_style="bold magenta")
        table.add_column("Aspect", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Primary Intent", interpretation.get("primary_intent", "Unknown"))
        table.add_row("Scope", interpretation.get("scope", "Unknown"))
        table.add_row("Complexity", interpretation.get("complexity", "Unknown"))
        table.add_row("Confidence", f"{interpretation.get('confidence', 0):.2f}")
        
        suggested_agents = interpretation.get("suggested_agents", [])
        table.add_row("Suggested Agents", ", ".join(suggested_agents))
        
        entities = interpretation.get("entities", [])
        if entities:
            table.add_row("Key Entities", ", ".join(entities[:5]))
            
        self.console.print(table)
        
    def _display_results(self, workflow_result: Dict[str, Any]):
        """Display the final workflow results"""
        
        if "error" in workflow_result:
            self.console.print(f"\n❌ [bold red]Workflow Error:[/bold red] {workflow_result['error']}")
            return
            
        # Display final response
        final_response = workflow_result.get("final_response", "No response generated")
        
        panel = Panel(
            final_response,
            title="🎯 Final Response",
            title_align="left",
            border_style="green",
            padding=(1, 2)
        )
        self.console.print(panel)
        
        # Display agent results summary
        agent_results = workflow_result.get("agent_results", {})
        if agent_results:
            self._display_agent_summary(agent_results)
            
    def _display_agent_summary(self, agent_results: Dict[str, Any]):
        """Display summary of individual agent results"""
        
        table = Table(title="🤖 Agent Results Summary", show_header=True, header_style="bold blue")
        table.add_column("Agent", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Key Findings", style="yellow")
        
        for agent_name, result in agent_results.items():
            if isinstance(result, dict):
                if "error" in result:
                    status = "❌ Error"
                    findings = result["error"]
                else:
                    status = "✅ Success"
                    
                    # Extract key findings based on agent type
                    if agent_name == "WebSearchAgent":
                        findings = f"Found {result.get('source_count', 0)} sources"
                    elif agent_name == "FileSearchAgent":
                        findings = f"Found {result.get('files_found', 0)} files"
                    elif agent_name == "InputInterpreterAgent":
                        findings = f"Intent: {result.get('primary_intent', 'Unknown')}"
                    else:
                        findings = "Completed successfully"
                        
                table.add_row(agent_name, status, findings)
                
        self.console.print(table)
    
    async def interactive_session(self):
        """Run an interactive session with the user"""
        
        self.console.print("\n🎯 [bold green]OpenAI Agentic Workflow System[/bold green]")
        self.console.print("Ask me anything! I'll search the web, analyze files, and provide comprehensive answers.")
        self.console.print("Type 'quit', 'exit', or 'bye' to end the session.\n")
        
        while True:
            try:
                # Get user input
                user_query = input("\n🔍 Your query: ").strip()
                
                if not user_query:
                    continue
                    
                # Check for exit commands
                if user_query.lower() in ['quit', 'exit', 'bye', 'q']:
                    self.console.print("\n👋 [bold blue]Thanks for using the Agentic Workflow System![/bold blue]")
                    break
                    
                # Check for special commands
                if user_query.lower().startswith('/'):
                    await self._handle_special_command(user_query)
                    continue
                    
                # Process the query
                await self.process_query(user_query)
                
            except KeyboardInterrupt:
                self.console.print("\n\n👋 [bold blue]Session interrupted. Goodbye![/bold blue]")
                break
            except Exception as e:
                self.console.print(f"\n❌ [bold red]Session error: {str(e)}[/bold red]")
                
    async def _handle_special_command(self, command: str):
        """Handle special session commands"""
        
        command = command.lower().strip()
        
        if command == "/help":
            self._show_help()
        elif command == "/history":
            self._show_session_history()
        elif command == "/agents":
            await self._show_agent_capabilities()
        elif command == "/clear":
            self.session_history = []
            self.console.print("📝 [green]Session history cleared.[/green]")
        else:
            self.console.print(f"❓ [yellow]Unknown command: {command}[/yellow]")
            self._show_help()
            
    def _show_help(self):
        """Display help information"""
        
        help_text = """
[bold cyan]Available Commands:[/bold cyan]
• /help     - Show this help message
• /history  - Show session query history  
• /agents   - Show agent capabilities
• /clear    - Clear session history
• quit/exit - End the session

[bold cyan]Usage Tips:[/bold cyan]
• Ask questions naturally - the system will interpret your intent
• Mention "web search" for internet queries
• Mention "files" or "code" for local searches
• Combine requests: "Search online for Python tutorials and find any Python files in this project"
        """
        
        panel = Panel(help_text, title="💡 Help", border_style="blue")
        self.console.print(panel)
        
    def _show_session_history(self):
        """Display session history"""
        
        if not self.session_history:
            self.console.print("📝 [yellow]No queries in session history.[/yellow]")
            return
            
        table = Table(title="📚 Session History", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim")
        table.add_column("Query", style="white")
        table.add_column("Intent", style="green")
        table.add_column("Agents Used", style="blue")
        
        for i, entry in enumerate(self.session_history[-10:], 1):  # Show last 10
            query = entry["query"][:50] + "..." if len(entry["query"]) > 50 else entry["query"]
            intent = entry["interpretation"].get("primary_intent", "Unknown")
            
            agents_used = []
            workflow_result = entry.get("workflow_result", {})
            agent_results = workflow_result.get("agent_results", {})
            
            for agent_name, result in agent_results.items():
                if isinstance(result, dict) and "error" not in result:
                    agents_used.append(agent_name.replace("Agent", ""))
                    
            agents_str = ", ".join(agents_used) if agents_used else "None"
            
            table.add_row(str(i), query, intent, agents_str)
            
        self.console.print(table)
        
    async def _show_agent_capabilities(self):
        """Display agent capabilities"""
        
        agents = [
            ("Input Interpreter", self.input_interpreter),
            ("Web Search", self.web_search_agent),
            ("File Search", self.file_search_agent),
            ("Handoff Coordinator", self.handoff_agent)
        ]
        
        for agent_name, agent in agents:
            capabilities = await agent.get_capabilities()
            
            table = Table(title=f"🤖 {agent_name} Agent", show_header=True, header_style="bold green")
            table.add_column("Capability", style="cyan")
            table.add_column("Description", style="white")
            
            capability_descriptions = {
                "base_communication": "Basic AI communication",
                "web_search": "Internet search and information retrieval",
                "information_retrieval": "Extract information from web sources",
                "content_summarization": "Summarize and analyze content",
                "source_verification": "Verify source credibility",
                "file_content_search": "Search within file contents",
                "filename_search": "Search by filename patterns",
                "code_analysis": "Analyze code structure and content",
                "text_extraction": "Extract text from various file formats",
                "pattern_matching": "Find patterns in text and code",
                "intent_recognition": "Understand user intent and goals",
                "entity_extraction": "Extract key entities and topics",
                "scope_determination": "Determine search scope (local vs web)",
                "agent_recommendation": "Recommend appropriate agents",
                "query_refinement": "Improve and refine queries",
                "context_analysis": "Analyze conversation context",
                "workflow_coordination": "Coordinate multi-agent workflows",
                "agent_orchestration": "Orchestrate agent interactions",
                "parallel_execution": "Execute agents simultaneously",
                "sequential_execution": "Execute agents in sequence",
                "result_synthesis": "Combine results from multiple agents",
                "dependency_management": "Manage agent dependencies"
            }
            
            for capability in capabilities:
                description = capability_descriptions.get(capability, "Advanced agent capability")
                table.add_row(capability.replace("_", " ").title(), description)
                
            self.console.print(table)
            self.console.print()  # Add spacing
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about the current session"""
        
        if not self.session_history:
            return {"total_queries": 0}
            
        total_queries = len(self.session_history)
        
        # Count intent types
        intent_counts = {}
        agent_usage = {}
        
        for entry in self.session_history:
            intent = entry["interpretation"].get("primary_intent", "unknown")
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
            
            workflow_result = entry.get("workflow_result", {})
            agent_results = workflow_result.get("agent_results", {})
            
            for agent_name in agent_results.keys():
                agent_usage[agent_name] = agent_usage.get(agent_name, 0) + 1
                
        return {
            "total_queries": total_queries,
            "intent_distribution": intent_counts,
            "agent_usage": agent_usage,
            "avg_agents_per_query": sum(agent_usage.values()) / total_queries if total_queries > 0 else 0
        }
    
    def add_search_directory(self, directory: str):
        """Add a directory for file searching"""
        self.file_search_agent.add_search_directory(directory)
        
    def remove_search_directory(self, directory: str):
        """Remove a directory from file searching"""
        self.file_search_agent.remove_search_directory(directory)