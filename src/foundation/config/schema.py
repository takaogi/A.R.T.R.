from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, List

class LLMParameter(BaseModel):
    """LLM generation parameters."""
    max_tokens: int = 1000
    temperature: float = 0.7
    top_p: float = 1.0
    reasoning_effort: str = "medium"

class LLMCapabilities(BaseModel):
    """Capabilities of the specific Model/Provider combination."""
    supports_structured_outputs: bool = False  # Native 'json_schema' support (Strict)
    supports_json_mode: bool = True           # Standard 'json_object' support
    force_schema_prompt_injection: bool = False # Safety override: Inject schema text even if structured output is used
    is_reasoning: bool = False # Whether the model utilizes internal reasoning (e.g. o1, gpt-5)

class LLMProfile(BaseModel):
    """Configuration for a specific LLM profile."""
    provider: str
    model_name: str
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None
    parameters: LLMParameter = Field(default_factory=LLMParameter)
    capabilities: LLMCapabilities = Field(default_factory=LLMCapabilities)

class SystemConfig(BaseModel):
    """Global system configuration."""
    active_profile: str = "default_local"
    debug_mode: bool = False
    debug_prompt_dump: bool = False # Dumps raw prompts to data/logs/prompts/
    enable_safety_bypass: bool = False # Inject strict safety overrides (Jailbreak)
    log_level: str = "INFO"

class MemoryConfig(BaseModel):
    """Configuration for Cognitive Memory."""
    conversation_limit: int = 20
    thought_limit: int = 10
    embedding_provider: str = Field("local", description="openai or local")
    local_embedding_model: str = Field("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", description="Model for local fastembed")
    include_thoughts_in_history: bool = Field(False, description="Whether to include 'thought' messages in LLM context")

class SearchConfig(BaseModel):
    """Configuration for Web Search."""
    google_api_key_env: str = "GOOGLE_API_KEY" # Env var name
    google_cse_id: Optional[str] = "c4bdecb34c7794e83"   # Default user provided
    use_llm_search: bool = True               # Attempt LLM search profile first
    
    @field_validator('google_cse_id')
    @classmethod
    def set_default_cse_id(cls, v: Optional[str]) -> str:
        if not v or not v.strip():
            return "c4bdecb34c7794e83"
        return v

class LocalModelPreset(BaseModel):
    name: str = Field(..., description="Display Name")
    repo_id: str = Field(..., description="HuggingFace Repo ID")
    filename: str = Field(..., description="GGUF Filename")
    description: str = Field("", description="Usage Hint (e.g. 12GB VRAM)")

class LocalLLMConfig(BaseModel):
    model_dir: str = Field("data/models/llm", description="Local Model Storage Path")
    default_model: str = Field("", description="Filename of default model")
    context_size: int = Field(8192, description="Default Context Size (n_ctx)")
    gpu_layers: int = Field(-1, description="Number of layers to offload (-1 = Max)")
    presets: List[LocalModelPreset] = Field(default_factory=list, description="Downloadable Presets")

class PacemakerConfig(BaseModel):
    """Global Default Configuration for Pacemaker."""
    default_auto_max_consecutive: int = 0

class AppConfig(BaseModel):
    """Root configuration object."""
    system: SystemConfig = Field(default_factory=SystemConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    local_llm: LocalLLMConfig = Field(default_factory=LocalLLMConfig)
    pacemaker: PacemakerConfig = Field(default_factory=PacemakerConfig)
    llm_profiles: Dict[str, LLMProfile] = Field(default_factory=dict)
    llm_strategies: Dict[str, str] = Field(default_factory=dict, description="Strategy -> ProfileName Mapping")
