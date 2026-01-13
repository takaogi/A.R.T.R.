import openai
from typing import Any, Dict, List, Optional
import os
from src.foundation.config import ConfigManager
from src.foundation.logging import logger
from src.foundation.types import Result
from .base import BaseLLMProvider
from ..schema import LLMRequest, LLMResponse

class OpenRouterProvider(BaseLLMProvider):
    """
    Provider for OpenRouter (OpenAI-compatible).
    Handles Generic OpenRouter models.
    """
    def __init__(self):
        super().__init__()
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        # Prefer OPENROUTER_API_KEY env var
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = "https://openrouter.ai/api/v1"
        
        if not api_key:
            logger.warning("OpenRouter API Key not found (OPENROUTER_API_KEY or OPENAI_API_KEY).")
            return

        try:
            self.client = openai.AsyncOpenAI(
                base_url=base_url,
                api_key=api_key,
                default_headers={
                    "HTTP-Referer": "https://github.com/hisaragi/A.R.T.R", # Placeholder
                    "X-Title": "A.R.T.R."
                }
            )
        except Exception as e:
            logger.warning(f"Failed to initialize OpenRouter Client: {e}")

    async def execute(self, request: LLMRequest) -> Result[LLMResponse]:
        if not self.client:
            return Result.fail("OpenRouter Client not initialized.")

        try:
            logger.debug(f"OpenRouter Request: Model={request.model}")
            
            kwargs = {
                "model": request.model,
                "messages": request.messages,
                "temperature": request.temperature,
            }

            # Reasoning models (like o1/o3/gpt-5.2 potentially) might treat temperature differently
            # For OpenRouter, we generally pass what the user asked, but some models fail with explicit temp.
            # We trust the config is set correctly for the model (e.g. low temp for reasoning).
            
            # Additional params if needed (top_p etc)
            # kwargs["top_p"] = request.top_p 
            
            # Support for reasoning_effort (gpt-5/o1/o3)
            # We pass it if provided. OpenRouter/OpenAI will handle validation.
            if request.reasoning_effort:
                kwargs["reasoning_effort"] = request.reasoning_effort

            if request.json_schema:
                # Native Structured Output (Strict)
                # OpenRouter follows OpenAI syntax
                schema_model = request.json_schema
                # If pydantic model, convert to dict
                if hasattr(schema_model, "model_json_schema"):
                    json_schema_dict = schema_model.model_json_schema()
                else:
                    json_schema_dict = schema_model
                
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "response", # schema name
                        "strict": True,
                        "schema": json_schema_dict
                    }
                }
                
                completion = await self.client.chat.completions.create(**kwargs)
                content = completion.choices[0].message.content
                
            elif request.force_json_mode:
                # Generic JSON Mode
                kwargs["response_format"] = {"type": "json_object"}
                completion = await self.client.chat.completions.create(**kwargs)
                content = completion.choices[0].message.content
                
            else:
                completion = await self.client.chat.completions.create(**kwargs)
                content = completion.choices[0].message.content

            return Result.ok(LLMResponse(
                content=content,
                model_name=completion.model,
                usage=completion.usage.model_dump() if completion.usage else {}
            ))

        except Exception as e:
            logger.error(f"OpenRouter Execution Error: {e}")
            return Result.fail(str(e))
