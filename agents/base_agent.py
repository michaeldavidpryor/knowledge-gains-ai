"""
Base Agent class for the Knowledge Gains Weightlifting App
Using OpenAI Assistants API with built-in tools
"""

import os
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncIterator
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


class BaseAgent(ABC):
    """Base class for all agents using OpenAI Assistants API"""

    def __init__(self, name: str, model: str = "gpt-4.1-2025-04-14", temperature: float = 0.7):
        self.name = name
        self.model = model
        self.temperature = temperature
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.assistant = None
        self.assistant_id = None
        self.thread_id = None
        self.tools = []
        
    async def initialize_assistant(self, instructions: str, tools: Optional[List[str]] = None):
        """Initialize or retrieve an assistant with specified tools"""
        # Define available tools
        available_tools = {
            "file_search": {"type": "file_search"},
            "code_interpreter": {"type": "code_interpreter"},
        }
        
        # Build tools list
        self.tools = []
        if tools:
            for tool in tools:
                if tool in available_tools:
                    self.tools.append(available_tools[tool])
        
        # Check if assistant already exists
        assistant_name = f"{self.name}_assistant"
        
        try:
            # List existing assistants
            assistants = await self.client.beta.assistants.list()
            for assistant in assistants.data:
                if assistant.name == assistant_name:
                    self.assistant = assistant
                    self.assistant_id = assistant.id
                    # Update assistant with latest configuration
                    self.assistant = await self.client.beta.assistants.update(
                        assistant_id=self.assistant_id,
                        model=self.model,
                        instructions=instructions,
                        tools=self.tools,
                        temperature=self.temperature
                    )
                    return
            
            # Create new assistant if not found
            self.assistant = await self.client.beta.assistants.create(
                name=assistant_name,
                model=self.model,
                instructions=instructions,
                tools=self.tools,
                temperature=self.temperature
            )
            self.assistant_id = self.assistant.id
            
        except Exception as e:
            raise Exception(f"Failed to initialize assistant: {str(e)}")
    
    async def create_thread(self):
        """Create a new conversation thread"""
        thread = await self.client.beta.threads.create()
        self.thread_id = thread.id
        return thread.id
    
    async def create_vector_store(self, name: str, file_paths: Optional[List[str]] = None):
        """Create a vector store for file search"""
        try:
            # Create vector store
            vector_store = await self.client.beta.vector_stores.create(
                name=name
            )
            
            # Upload files if provided
            if file_paths:
                file_streams = []
                for path in file_paths:
                    with open(path, "rb") as file:
                        file_streams.append(file)
                
                # Upload files to vector store
                file_batch = await self.client.beta.vector_stores.file_batches.upload_and_poll(
                    vector_store_id=vector_store.id,
                    files=file_streams
                )
                
            # Update assistant with vector store
            await self.client.beta.assistants.update(
                assistant_id=self.assistant_id,
                tool_resources={
                    "file_search": {
                        "vector_store_ids": [vector_store.id]
                    }
                }
            )
            
            return vector_store.id
            
        except Exception as e:
            raise Exception(f"Failed to create vector store: {str(e)}")
    
    async def upload_file_for_code_interpreter(self, file_path: str):
        """Upload a file for code interpreter"""
        try:
            with open(file_path, "rb") as file:
                uploaded_file = await self.client.files.create(
                    file=file,
                    purpose="assistants"
                )
            
            # Attach file to thread for code interpreter
            if self.thread_id:
                await self.client.beta.threads.update(
                    thread_id=self.thread_id,
                    tool_resources={
                        "code_interpreter": {
                            "file_ids": [uploaded_file.id]
                        }
                    }
                )
            
            return uploaded_file.id
            
        except Exception as e:
            raise Exception(f"Failed to upload file: {str(e)}")

    async def send_message(
        self, message: str, file_ids: Optional[List[str]] = None, stream: bool = False
    ) -> str:
        """Send a message using Assistants API"""
        if not self.assistant_id:
            raise Exception("Assistant not initialized. Call initialize_assistant() first.")
        
        if not self.thread_id:
            await self.create_thread()
        
        try:
            # Create message in thread
            message_params = {
                "thread_id": self.thread_id,
                "role": "user",
                "content": message
            }
            if file_ids:
                message_params["attachments"] = [{"file_id": fid} for fid in file_ids]
                
            await self.client.beta.threads.messages.create(**message_params)
            
            # Create run
            run = await self.client.beta.threads.runs.create(
                thread_id=self.thread_id,
                assistant_id=self.assistant_id
            )
            
            if stream:
                return await self._handle_streaming_run(run.id)
            else:
                return await self._handle_run(run.id)
                
        except Exception as e:
            return f"Error communicating with OpenAI: {str(e)}"
    
    async def _handle_run(self, run_id: str) -> str:
        """Handle a non-streaming run"""
        while True:
            run = await self.client.beta.threads.runs.retrieve(
                thread_id=self.thread_id,
                run_id=run_id
            )
            
            if run.status == "completed":
                # Get the latest message
                messages = await self.client.beta.threads.messages.list(
                    thread_id=self.thread_id,
                    limit=1
                )
                
                if messages.data:
                    message_content = messages.data[0].content[0]
                    if hasattr(message_content, 'text'):
                        return message_content.text.value
                    return str(message_content)
                return "No response generated"
                
            elif run.status == "failed":
                return f"Run failed: {run.last_error}"
            elif run.status == "cancelled":
                return "Run was cancelled"
            elif run.status == "expired":
                return "Run expired"
            elif run.status == "requires_action":
                # Handle function calls if needed
                # For now, we'll skip this as we're using built-in tools
                pass
            
            # Wait before checking again
            await asyncio.sleep(0.5)
    
    async def _handle_streaming_run(self, run_id: str) -> str:
        """Handle a streaming run and return full response"""
        full_response = ""
        
        async with self.client.beta.threads.runs.stream(
            thread_id=self.thread_id,
            assistant_id=self.assistant_id
        ) as stream:
            async for event in stream:
                if event.event == "thread.message.delta":
                    if hasattr(event.data, 'delta') and hasattr(event.data.delta, 'content'):
                        for content in event.data.delta.content:
                            if hasattr(content, 'text') and hasattr(content.text, 'value'):
                                full_response += content.text.value
                                
        return full_response

    async def send_message_stream_generator(
        self, message: str, file_ids: Optional[List[str]] = None
    ) -> AsyncIterator[str]:
        """Send a message and yield streaming response chunks"""
        if not self.assistant_id:
            raise Exception("Assistant not initialized. Call initialize_assistant() first.")
        
        if not self.thread_id:
            await self.create_thread()
        
        try:
            # Create message in thread
            message_params = {
                "thread_id": self.thread_id,
                "role": "user",
                "content": message
            }
            if file_ids:
                message_params["attachments"] = [{"file_id": fid} for fid in file_ids]
                
            await self.client.beta.threads.messages.create(**message_params)
            
            # Stream the run
            async with self.client.beta.threads.runs.stream(
                thread_id=self.thread_id,
                assistant_id=self.assistant_id
            ) as stream:
                async for event in stream:
                    if event.event == "thread.message.delta":
                        if hasattr(event.data, 'delta') and hasattr(event.data.delta, 'content'):
                            for content in event.data.delta.content:
                                if hasattr(content, 'text') and hasattr(content.text, 'value'):
                                    yield content.text.value
                                    
        except Exception as e:
            yield f"Error communicating with OpenAI: {str(e)}"

    async def search_web(self, query: str) -> Dict[str, Any]:
        """Web search using function calling (to be implemented with custom functions)"""
        # Note: Web search isn't a built-in tool in Assistants API
        # This would need to be implemented using function calling
        # For now, returning a placeholder
        return {
            "status": "not_implemented",
            "message": "Web search requires custom function implementation"
        }

    @abstractmethod
    async def process(self, input_data: Any) -> Dict[str, Any]:
        """Process input data and return results"""
        pass

    async def clear_thread(self):
        """Start a new conversation thread"""
        thread = await self.client.beta.threads.create()
        self.thread_id = thread.id
        return thread.id

    async def get_thread_messages(self, limit: int = 20) -> List[Dict[str, str]]:
        """Get messages from current thread"""
        if not self.thread_id:
            return []
        
        messages = await self.client.beta.threads.messages.list(
            thread_id=self.thread_id,
            limit=limit
        )
        
        formatted_messages = []
        for msg in reversed(messages.data):
            content = ""
            if msg.content:
                for content_item in msg.content:
                    if hasattr(content_item, 'text'):
                        content += content_item.text.value
            
            formatted_messages.append({
                "role": msg.role,
                "content": content
            })
        
        return formatted_messages

    async def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities"""
        capabilities = ["assistants_api", "streaming_responses"]
        if "file_search" in [tool.get("type") for tool in self.tools]:
            capabilities.append("file_search")
        if "code_interpreter" in [tool.get("type") for tool in self.tools]:
            capabilities.append("code_interpreter")
        return capabilities
