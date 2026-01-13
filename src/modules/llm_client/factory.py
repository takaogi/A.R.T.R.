import importlib
from src.foundation.types import Result
from .prompts.base import BaseBuilder

class PromptFactory:
    """
    Responsible for loading the correct Strategy/Builder for a given prompt name.
    Does NOT handle execution logic anymore.
    """
    
    @staticmethod
    def get_builder(prompt_name: str) -> Result[BaseBuilder]:
        try:
            # Dynamic Import: src.modules.llm_client.prompts.{name}.builder
            module_path = f"src.modules.llm_client.prompts.{prompt_name}.builder"
            module = importlib.import_module(module_path)
            
            # Assume the class is named 'Builder' or find subclass of BaseBuilder
            if hasattr(module, "Builder"):
                from .prompts.echo import EchoBuilder
                return Result.ok(EchoBuilder())
            elif prompt_name == "character_convert":
                from .prompts.character_convert import CharacterConvertBuilder
                return Result.ok(CharacterConvertBuilder())
            elif prompt_name == "character_generate":
                from .prompts.character_generate.builder import CharacterGenerateBuilder
                return Result.ok(CharacterGenerateBuilder())
            elif prompt_name == "cognitive":
                from .prompts.cognitive.builder import CognitivePromptBuilder
                return Result.ok(CognitivePromptBuilder())
            elif prompt_name == "memory_consolidate":
                from .prompts.memory_consolidate.builder import MemoryConsolidateBuilder
                return Result.ok(MemoryConsolidateBuilder())
            elif prompt_name == "web_search_summary":
                from .prompts.web_search_summary.builder import WebSearchSummaryBuilder
                return Result.ok(WebSearchSummaryBuilder())
            else:
                return Result.fail(f"Prompt '{prompt_name}' not found.")
                
        except ImportError:
            return Result.fail(f"Prompt '{prompt_name}' not found (Module '{module_path}' missing).")
        except Exception as e:
            return Result.fail(f"Failed to load builder for '{prompt_name}': {e}")
