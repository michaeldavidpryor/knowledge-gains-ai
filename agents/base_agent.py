"""
Base Agent class for the Knowledge Gains Weightlifting App
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


class BaseAgent(ABC):
    """Base class for all agents in the Knowledge Gains system"""

    def __init__(self, name: str, model: str = "gpt-4", temperature: float = 0.7):
        self.name = name
        self.model = model
        self.temperature = temperature
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversation_history: List[Dict[str, str]] = []

    async def send_message(
        self, message: str, system_prompt: Optional[str] = None
    ) -> str:
        """Send a message to OpenAI and get response"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add conversation history
        messages.extend(self.conversation_history)

        # Add current message
        messages.append({"role": "user", "content": message})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=4000,  # Increased for detailed workout programs
            )

            assistant_response = (
                response.choices[0].message.content or "No response generated"
            )

            # Update conversation history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_response,
            })

            # Keep only last 10 exchanges to manage context
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

            return assistant_response

        except Exception as e:
            return f"Error communicating with OpenAI: {str(e)}"

    @abstractmethod
    async def process(self, input_data: Any) -> Dict[str, Any]:
        """Process input data and return results"""
        pass

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []

    async def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities"""
        return ["base_communication"]
