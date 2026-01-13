from src.foundation.config import ConfigManager, LLMProfile

class ModelRouter:
    """
    Determines which Model Profile to use based on the task name.
    """
    def __init__(self):
        self.config_manager = ConfigManager.get_instance()

    def get_profile(self, prompt_name: str) -> LLMProfile:
        config = self.config_manager.config
        
        # 1. Strategy Lookup
        strategies = config.llm_strategies
        profile_key = strategies.get(prompt_name)
        
        # Fallback 1: Try system default if defined (removed by user request, but schema has default)
        if not profile_key:
             # Try to find a reasonable default
             if "roleplay" in config.llm_profiles:
                 profile_key = "roleplay"
             elif "gpt-5-mini(openrouter)" in config.llm_profiles:
                 profile_key = "gpt-5-mini(openrouter)"
             elif "chat_cost_effective" in config.llm_profiles:
                 profile_key = "chat_cost_effective"
             else:
                 # Take first available
                 profile_key = list(config.llm_profiles.keys())[0]

        if profile_key not in config.llm_profiles:
            raise ValueError(f"Profile '{profile_key}' not found in llm_profiles config.")
            
        return config.llm_profiles[profile_key]
