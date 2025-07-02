#!/usr/bin/env python3
"""
Main entry point for the OpenAI Agentic Workflow System
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents import WorkflowCoordinator


async def main():
    """Main function to run the agentic workflow system"""
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable is not set.")
        print("Please set your OpenAI API key in a .env file or environment variable.")
        print("Example: OPENAI_API_KEY=sk-your-api-key-here")
        return
    
    # Initialize the workflow coordinator
    # You can specify custom search directories for file searching
    search_directories = [
        ".",  # Current directory
        # Add more directories as needed
        # "~/Documents",
        # "/path/to/your/project"
    ]
    
    coordinator = WorkflowCoordinator(search_directories=search_directories)
    
    # Check if we have command line arguments for single query mode
    if len(sys.argv) > 1:
        # Single query mode
        query = " ".join(sys.argv[1:])
        print(f"🚀 Processing single query: {query}")
        
        result = await coordinator.process_query(query)
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            sys.exit(1)
        else:
            print("✅ Query processed successfully!")
            
    else:
        # Interactive session mode
        await coordinator.interactive_session()


def run_example_queries():
    """Run some example queries to demonstrate the system"""
    
    async def example_session():
        coordinator = WorkflowCoordinator()
        
        example_queries = [
            "What is machine learning and find any Python ML files in this project",
            "Search for recent developments in AI agents",
            "Find all configuration files in this project",
            "Explain what OpenAI GPT-4 is and search for any related code",
            "What are the best practices for Python development"
        ]
        
        print("🎯 Running example queries...\n")
        
        for i, query in enumerate(example_queries, 1):
            print(f"\n{'='*60}")
            print(f"📝 Example {i}: {query}")
            print('='*60)
            
            result = await coordinator.process_query(query)
            
            if "error" in result:
                print(f"❌ Error: {result['error']}")
            else:
                print("✅ Example completed successfully!")
                
            print("\n" + "-"*40)
            
    asyncio.run(example_session())


if __name__ == "__main__":
    # Check if user wants to run examples
    if len(sys.argv) > 1 and sys.argv[1] == "--examples":
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ Error: OPENAI_API_KEY environment variable is not set.")
            print("Please set your OpenAI API key in a .env file or environment variable.")
            sys.exit(1)
        run_example_queries()
    else:
        asyncio.run(main())