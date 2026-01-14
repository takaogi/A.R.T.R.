from typing import Any, Dict
from src.foundation.logging import logger
from src.foundation.types import Result
from src.foundation.types import Result
from .factory import PromptFactory
from .providers.openrouter import OpenRouterProvider
from .router import ModelRouter
from .schema import LLMRequest, LLMResponse
from .providers.openai import OpenAIProvider
from .providers.openrouter import OpenRouterProvider
import os

class LLMClient:
    """
    High-level client for executing LLM tasks.
    Orchestrates Factory, Router, and Providers.
    """
    
    def __init__(self):
        self.router = ModelRouter()
        # Cache providers
        self.providers = {}

    def _get_provider(self, provider_name: str):
        if provider_name in self.providers:
            return self.providers[provider_name]
        
        # Determine provider class dynamically or via generic mapping
        if provider_name == "openai":
            p = OpenAIProvider()
            self.providers[provider_name] = p
            return p
        elif provider_name == "openrouter":
            p = OpenRouterProvider()
            self.providers[provider_name] = p
            return p
            
        logger.error(f"Provider '{provider_name}' implementation not found.")
        return None

    async def execute(self, prompt_name: str, data: Dict[str, Any] = None, 
                      override_builder: Any = None, override_profile: Any = None) -> Result[LLMResponse]:
        """
        Executes the specified prompt strategy.
        Returns full LLMResponse (content, usage, etc).
        If overrides are provided, uses them instead of Factory/Router lookups.
        """
        data = data or {}
        
        # 1. Load Builder (Strategy)
        if override_builder:
            builder = override_builder
        else:
            res_builder = PromptFactory.get_builder(prompt_name)
            if not res_builder.success:
                return Result.fail(res_builder.error)
            builder = res_builder.data

        # 2. Routing (Model Profile)
        if override_profile:
            profile = override_profile
        else:
            try:
                profile = self.router.get_profile(prompt_name)
            except Exception as e:
                return Result.fail(f"Routing Error: {e}")

        # 3. Build Messages
        try:
            messages = builder.build_messages(data, profile)
        except Exception as e:
            return Result.fail(f"Builder Error (Messages): {e}")

        # 4. Build Schema (Optional)
        try:
            schema = builder.build_schema(data, profile)
            # Schema can be None now (Natural Language Mode)
        except Exception as e:
            return Result.fail(f"Builder Error (Schema): {e}")

        # 5. Get Provider
        provider = self._get_provider(profile.provider)
        if not provider:
            return Result.fail(f"Provider '{profile.provider}' not supported or initialized.")

        # 6. Execute Request (Capability-based Routing)
        req_json_schema = None
        req_force_json = False

        if schema is not None:
            if hasattr(profile, 'capabilities'):
                if profile.capabilities.supports_structured_outputs:
                    req_json_schema = schema
                elif profile.capabilities.supports_json_mode:
                    req_force_json = True
            else:
                # Fallback if capabilities not defined (e.g. legacy profiles)
                # Default to generic JSON mode for OpenAI/OpenRouter if schema exists
                if profile.provider in ["openai", "openrouter"]:
                     req_force_json = True

        # Resolve connection details
        api_key = None
        if profile.api_key_env:
            api_key = os.getenv(profile.api_key_env)
            
        req = LLMRequest(
            messages=messages,
            model=profile.model_name,
            temperature=profile.parameters.temperature,
            reasoning_effort=profile.parameters.reasoning_effort,
            json_schema=req_json_schema,
            force_json_mode=req_force_json,
            tools=data.get("tools"),
            base_url=profile.base_url,
            api_key=api_key
        )

        # Debug: Dump Prompt
        try:
            from src.foundation.config import ConfigManager
            cfg = ConfigManager.get_instance().config
            if cfg and cfg.system.debug_prompt_dump:
                import json
                import datetime
                from pathlib import Path
                
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                log_dir = Path("data/logs/prompts")
                log_dir.mkdir(parents=True, exist_ok=True)
                
                log_file = log_dir / f"{ts}_{prompt_name}.txt"
                
                with open(log_file, "w", encoding="utf-8") as f:
                    f.write(f"Prompt Strategy: {prompt_name}\n")
                    f.write(f"Model: {profile.model_name}\n")
                    f.write("-" * 40 + "\n")
                    for msg in messages:
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')
                        f.write(f"\n[{role.upper()}]\n{content}\n")
                        f.write("-" * 20 + "\n")
                        
                logger.debug(f"Dumped prompt to {log_file}")
        except Exception as e:
            logger.warning(f"Failed to dump prompt: {e}")

        logger.info(f"LLMClient Executing: {prompt_name} -> {profile.model_name} (via {profile.provider})")
        return await provider.execute(req)
