from typing import List, Optional, Type, TypeVar, Union, Any
from pydantic import BaseModel
from openai import AsyncOpenAI, OpenAIError
from src.config import settings
from src.utils.logger import logger

T = TypeVar("T", bound=BaseModel)

class LLMClient:
    """
    Unified client for LLM interactions.
    Simplified to two core methods: Local (Text) and OpenAI (Structured).
    """
    
    _client: Optional[AsyncOpenAI] = None

    @classmethod
    def get_client(cls) -> AsyncOpenAI:
        """
        Lazily initializes and returns the AsyncOpenAI client.
        """
        if cls._client is None:
            # If provider is OpenAI, we should NOT use the custom base_url unless specifically intended (unlikely if it's localhost)
            # To be safe, we only use base_url if provider is NOT openai OR if base_url doesn't look like localhost when provider IS openai.
            # Simpler: If provider is 'openai', force base_url to None to use official API.
            
            target_base_url = settings.OPENAI_BASE_URL
            if settings.LLM_PROVIDER == "openai":
                # Explicitly force official URL to override any local environment variables
                target_base_url = "https://api.openai.com/v1/"
                
            cls._client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=target_base_url
            )
            logger.debug(f"AsyncOpenAI Client initialized. Provider: {settings.LLM_PROVIDER}, Base: {target_base_url}")
        return cls._client

    @classmethod
    async def request_text(cls, messages: List[dict], model: str, reasoning_effort: Optional[str] = None) -> str:
        """
        [Local / Text]
        Basic chat completion returning plain text.
        Use this for Local LLMs or when structured output is not supported/needed (e.g. Reflex output).
        """
        client = cls.get_client()
        
        # Prepare arguments
        kwargs = {
            "model": model,
            "messages": messages,
        }
        
        # Add reasoning_effort if provided and supported (Optimistic approach: add if not None)
        if reasoning_effort:
             kwargs["reasoning_effort"] = reasoning_effort

        try:
            logger.debug(f"Sending TEXT request to {model} (Reasoning: {reasoning_effort})")
            response = await client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            logger.debug(f"Received response from {model}. Length: {len(content) if content else 0}")
            
            # Log Trace
            cls._log_trace(model, messages, content)
            
            return content if content else ""
        except OpenAIError as e:
            cls._log_trace(model, messages, None, str(e))
            logger.error(f"API Error (Text): {e}")
            raise
        except Exception as e:
            cls._log_trace(model, messages, None, str(e))
            logger.exception(f"Unexpected Error (Text): {e}")
            raise

    @classmethod
    async def request_structured(
        cls, 
        messages: List[dict], 
        response_model: Type[T], 
        model: str,
        reasoning_effort: Optional[str] = None
    ) -> T:
        """
        [OpenAI / Structured]
        Native Structured Outputs (beta.chat.completions.parse).
        Use this when running Core Thinking on OpenAI to get robust JSON objects.
        """
        client = cls.get_client()
        
        # Prepare arguments
        kwargs = {
            "model": model,
            "messages": messages,
            "response_format": response_model,
        }
        
        # Add reasoning_effort if provided
        if reasoning_effort:
             kwargs["reasoning_effort"] = reasoning_effort

        try:
            logger.debug(f"Sending STRUCTURED request to {model} (Schema: {response_model.__name__}, Reasoning: {reasoning_effort})")
            completion = await client.beta.chat.completions.parse(**kwargs)
            
            parsed_response = completion.choices[0].message.parsed
            
            if not parsed_response:
                logger.error(f"Structured output parsing failed for {model}")
                raise ValueError("Model failed to produce valid structured output.")
                
            logger.debug(f"Structured response parsed successfully: {type(parsed_response)}")
            
            # Log Trace (Dump model to dict for JSON serialization)
            try:
                resp_dict = parsed_response.model_dump()
            except:
                resp_dict = str(parsed_response)
            cls._log_trace(model, messages, resp_dict)
            
            return parsed_response

        except OpenAIError as e:
            cls._log_trace(model, messages, None, str(e))
            logger.error(f"API Error (Structured): {e}")
            if hasattr(e, 'body') and isinstance(e.body, dict) and e.body.get('code') == 'refusal':
                 logger.warning(f"Model Refusal: {e.body.get('message')}")
            raise

        except Exception as e:
            cls._log_trace(model, messages, None, str(e))
            logger.exception(f"Unexpected Error (Structured): {e}")
            raise

    @classmethod
    async def request_embeddings(cls, input: Union[str, List[str]], model: str = None) -> List[List[float]]:
        """
        Request embeddings for a string or list of strings.
        Always returns a list of embeddings (List[List[float]]).
        """
        client = cls.get_client()
        target_model = model or settings.EMBEDDING_MODEL
        
        # Ensure input is list
        if isinstance(input, str):
            input = [input]
            
        try:
            response = await client.embeddings.create(
                input=input,
                model=target_model
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Embedding API Error: {e}")
            raise

    @classmethod
    def _log_trace(cls, model: str, messages: List[dict], response_content: Any, error: str = None):
        """
        Appends the full transaction details to logs/llm_trace.jsonl for debugging.
        """
        import json
        import datetime
        from pathlib import Path
        
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "llm_trace.jsonl"
        
        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "model": model,
            "messages": messages,
            "response": response_content,
            "error": error
        }
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
            # Console Output (Summary)
            msg_summary = str(messages)[:100] + "..." if len(str(messages)) > 100 else str(messages)
            resp_summary = str(response_content)[:100] + "..." if len(str(response_content)) > 100 else str(response_content)
            logger.info(f"LLM Trace | Model: {model} | In: {msg_summary} | Out: {resp_summary} | Error: {error}")

        except Exception as e:
            logger.error(f"Failed to write LLM trace: {e}")

