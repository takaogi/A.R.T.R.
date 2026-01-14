import openai
from typing import Any, Dict, List, Optional
from src.foundation.config import ConfigManager
from src.foundation.logging import logger
from src.foundation.types import Result
from .base import BaseLLMProvider
from ..schema import LLMRequest, LLMResponse

class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        super().__init__()
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        cm = ConfigManager.get_instance()
        try:
            self.client = openai.AsyncOpenAI()
        except Exception as e:
            logger.warning(f"Failed to initialize AsyncOpenAI Client: {e}")

    async def execute(self, request: LLMRequest) -> Result[LLMResponse]:
        # Determine Client (Default or Temp for Custom URL)
        active_client = self.client
        is_custom_connection = False

        if request.base_url or request.api_key:
            try:
                # Create transient client for this request
                active_client = openai.AsyncOpenAI(
                    base_url=request.base_url,
                    api_key=request.api_key or os.getenv("OPENAI_API_KEY") or "dummy" 
                )
                is_custom_connection = True
            except Exception as e:
                return Result.fail(f"Failed to create custom OpenAI client: {e}")
        
        if not active_client:
            return Result.fail("OpenAI Client not initialized.")

        try:
            logger.debug(f"OpenAI Request: Model={request.model} (CustomURL={is_custom_connection})")
            
            # Use Responses API?
            # Disable if custom connection (Ollama/Generic likely don't support it)
            use_responses_api = True if (request.json_schema or (request.tools and len(request.tools) > 0)) else False
            if is_custom_connection:
                use_responses_api = False

            if use_responses_api:
                logger.debug("Using OpenAI Responses API (Async)")
                
                api_args = {
                    "model": request.model,
                    "input": request.messages,
                    "tools": request.tools or []
                }
                
                # Reasoning Effort
                is_reasoning_model = any(k in request.model for k in ["o1", "o3", "gpt-5"])
                if is_reasoning_model and request.reasoning_effort and request.reasoning_effort != "none":
                     api_args["reasoning"] = {"effort": request.reasoning_effort}
                else:
                     api_args["temperature"] = request.temperature

                # Structured Outputs
                if request.json_schema:
                    import pydantic
                    fmt = None
                    schema_obj = request.json_schema
                    
                    if isinstance(schema_obj, type) and issubclass(schema_obj, pydantic.BaseModel):
                        json_schema = schema_obj.model_json_schema()
                        
                        def enforce_strict(s):
                            if s.get("type") == "object":
                                s["additionalProperties"] = False
                            if "properties" in s:
                                for v in s["properties"].values():
                                    if isinstance(v, dict):
                                        enforce_strict(v)
                            if "$defs" in s:
                                for v in s["defs" if "defs" in s else "$defs"].values():
                                    if isinstance(v, dict):
                                        enforce_strict(v)
                            return s

                        json_schema = enforce_strict(json_schema)

                        fmt = {
                            "type": "json_schema",
                            "name": schema_obj.__name__,
                            "strict": True,
                            "schema": json_schema
                        }
                    elif isinstance(schema_obj, dict):
                        if schema_obj.get("type") == "json_schema" and "json_schema" in schema_obj:
                             inner = schema_obj["json_schema"]
                             fmt = {
                                 "type": "json_schema",
                                 "name": inner.get("name", "output"),
                                 "strict": inner.get("strict", True),
                                 "schema": inner.get("schema")
                             }
                        else:
                             fmt = schema_obj
                    
                    if fmt:
                        api_args["text"] = {"format": fmt}
                    
                response = await active_client.responses.create(**api_args)
                
                content = response.output_text
                
                return Result.ok(LLMResponse(
                    content=content,
                    model_name=response.model,
                    usage={} 
                ))

            else:
                # Standard Chat Completion (Async)
                kwargs = {
                    "model": request.model,
                    "messages": request.messages,
                    "temperature": request.temperature,
                }

                is_reasoning_model = any(k in request.model for k in ["o1", "o3", "gpt-5"])
                if is_reasoning_model and request.reasoning_effort:
                    if request.reasoning_effort != "none":
                        kwargs["reasoning_effort"] = request.reasoning_effort
                        if "temperature" in kwargs: del kwargs["temperature"]
    
                if request.force_json_mode:
                        kwargs["response_format"] = {"type": "json_object"}
    
                completion = await active_client.chat.completions.create(**kwargs)
                content = completion.choices[0].message.content
    
                return Result.ok(LLMResponse(
                    content=content,
                    model_name=completion.model,
                    usage=completion.usage.model_dump() if completion.usage else {}
                ))

        except Exception as e:
            logger.error(f"OpenAI Execution Error: {e}")
            return Result.fail(str(e))
