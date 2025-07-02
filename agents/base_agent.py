"""
Base Agent class for Knowledge Gains Weightlifting App
Refactored to use OpenAI Responses API (stateful, tool-augmented)
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncIterator, Union

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


class BaseAgent(ABC):
    """Base class for all AI agents powered by the OpenAI Responses API"""

    def __init__(
        self,
        name: str,
        model: str = "gpt-4.1-2025-04-14",
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
    ):
        self.name = name
        self.model = model
        self.temperature = temperature
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Stateful conversation handled by Responses API via previous_response_id
        self._last_response_id: Optional[str] = None

        # Default tools (e.g. file_search / web_search / code_interpreter)
        self.tools = tools or []

    # ---------------------------------------------------------------------
    # Core messaging helpers
    # ---------------------------------------------------------------------
    async def send_message(
        self,
        message: Union[str, List[Dict[str, Any]]],
        extra_tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
    ) -> str:
        """Send a message via Responses API and return full output text.

        Args:
            message: Either a plain user string or an array of input items per
                     Responses API spec.
            extra_tools: Additional tools to include for this request.
            stream: If True, return full response after streaming; otherwise
                     synchronous call.
        """
        input_items: List[Any]
        if isinstance(message, str):
            # Convert to minimal input item list
            input_items = [{"role": "user", "content": message, "type": "input_text"}]
        else:
            # Assume already correctly structured
            input_items = message  # type: ignore

        tools = self.tools.copy()
        if extra_tools:
            tools.extend(extra_tools)

        try:
            if stream:
                # Streaming request
                response_stream = await self.client.responses.create(
                    model=self.model,
                    input=input_items,
                    previous_response_id=self._last_response_id,
                    tools=tools or None,
                    temperature=self.temperature,
                    stream=True,
                )
                full_text = ""
                async for event in response_stream:
                    if event.type == "response.output_text.delta":
                        full_text += event.delta
                # After streaming finishes, retrieve final response to get id
                if hasattr(response_stream, "response") and response_stream.response:
                    self._last_response_id = response_stream.response.id  # type: ignore
                return full_text

            # Synchronous
            response = await self.client.responses.create(
                model=self.model,
                input=input_items,
                previous_response_id=self._last_response_id,
                tools=tools or None,
                temperature=self.temperature,
            )
            self._last_response_id = response.id
            # Prefer output_text shortcut if available
            if hasattr(response, "output_text") and response.output_text:
                return response.output_text
            # Fall back to concatenating messages
            if response.output:
                return "\n".join(
                    piece.text for out in response.output for piece in getattr(out, "content", []) if hasattr(piece, "text")
                )
            return ""
        except Exception as e:
            return f"Error communicating with OpenAI Responses API: {str(e)}"

    async def send_message_stream_generator(
        self,
        message: Union[str, List[Dict[str, Any]]],
        extra_tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """Yield streamed output_text deltas from Responses API."""
        input_items: List[Any]
        if isinstance(message, str):
            input_items = [{"role": "user", "content": message, "type": "input_text"}]
        else:
            input_items = message  # type: ignore

        tools = self.tools.copy()
        if extra_tools:
            tools.extend(extra_tools)

        try:
            stream = await self.client.responses.create(
                model=self.model,
                input=input_items,
                previous_response_id=self._last_response_id,
                tools=tools or None,
                temperature=self.temperature,
                stream=True,
            )
            async for event in stream:
                if event.type == "response.output_text.delta":
                    yield event.delta
            # Save last_response_id if available
            if hasattr(stream, "response") and stream.response:
                self._last_response_id = stream.response.id  # type: ignore
        except Exception as e:
            yield f"Error communicating with OpenAI Responses API: {str(e)}"

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def reset_conversation(self):
        """Clear stored response id (start new conversation)."""
        self._last_response_id = None

    @abstractmethod
    async def process(self, input_data: Any) -> Dict[str, Any]:
        """Process input and produce result."""
        pass

    async def get_capabilities(self) -> List[str]:
        return [
            "responses_api",
            "stateful_conversation",
            "streaming_responses",
        ]
