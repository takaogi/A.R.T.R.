import asyncio
import traceback
from typing import Optional, Dict, Any, List
from pathlib import Path

from src.foundation.config import ConfigManager
from src.foundation.logging import logger
from src.modules.llm_client.client import LLMClient
from src.modules.memory.manager import MemoryManager
from src.modules.character.manager import CharacterStateManager
from src.modules.character.schema import CharacterProfile
from src.modules.character.loader import CharXLoader
from src.modules.cognitive.engine import CognitiveEngine
from src.modules.cognitive.tools.registry import ToolRegistry
from src.modules.llm_client.prompts.cognitive.schema import CognitiveResponse
from src.modules.local_llm.manager import LocalModelManager

# Tool Imports
from src.modules.cognitive.tools.implementations.communication import TalkTool, AdjustRapportAction, AdjustRapportTool
from src.modules.cognitive.tools.implementations.memory import RememberTool, RecallTool
from src.modules.cognitive.tools.implementations.knowledge import WebSearchTool
from src.modules.cognitive.tools.implementations.schedule import ScheduleEventTool, CheckScheduleTool, EditScheduleTool
from src.modules.cognitive.tools.implementations.perception import GazeTool
from src.modules.cognitive.tools.implementations.meta import UpdateCoreMemoryTool

class CoreController:
    """
    Facade for the A.R.T.R. system.
    Handles initialization, character loading, and the main cognitive loop.
    Serves as the primary interface for the UI.
    """
    
    def __init__(self):
        self.config_manager: Optional[ConfigManager] = None
        self.llm_client: Optional[LLMClient] = None
        self.memory_manager: Optional[MemoryManager] = None
        self.character_manager: Optional[CharacterStateManager] = None
        self.engine: Optional[CognitiveEngine] = None
        self.tool_registry: Optional[ToolRegistry] = None
        self.local_model_manager: Optional[LocalModelManager] = None
        
        self.current_profile: Optional[CharacterProfile] = None
        self._is_initialized = False

    async def initialize_system(self, config_path: str = "config.yaml"):
        """
        Bootstraps the foundation modules.
        """
        logger.info("CoreController: Initializing System...")
        
        # 1. Config
        self.config_manager = ConfigManager.get_instance()
        self.config_manager.load_config(config_path)
        
        # 2. LLM Client
        self.local_model_manager = LocalModelManager(self.config_manager)
        self.llm_client = LLMClient()
        
        # 3. Memory & Tools
        self.memory_manager = MemoryManager(self.config_manager)
        self.tool_registry = ToolRegistry()
        
        # Register Default Tools
        self._register_tools()
        
        self._is_initialized = True
        logger.info("CoreController: System Initialized.")

    def _register_tools(self):
        """Registers all default tools to the registry."""
        if not self.tool_registry:
            return

        # Communication
        self.tool_registry.register("talk", TalkTool())
        self.tool_registry.register("adjust_rapport", AdjustRapportTool())
        
        # Memory
        self.tool_registry.register("remember", RememberTool())
        self.tool_registry.register("recall", RecallTool())
        
        # Knowledge
        # WebSearch needs Config and LLM. Engine might not inject Config? 
        # Inspecting Engine: It injects 'memory' and 'character' manager. 
        # Controller should probably prep this one.
        web_tool = WebSearchTool(config_manager=self.config_manager, llm_client=self.llm_client)
        self.tool_registry.register("web_search", web_tool)
        
        # Schedule
        self.tool_registry.register("schedule_event", ScheduleEventTool())
        self.tool_registry.register("check_schedule", CheckScheduleTool())
        self.tool_registry.register("edit_schedule", EditScheduleTool())
        
        # Perception
        self.tool_registry.register("gaze", GazeTool())
        
        # Meta
        self.tool_registry.register("update_core_memory", UpdateCoreMemoryTool())

    async def load_character(self, output_path: str = None, profile_obj: CharacterProfile = None):
        """
        Loads a character and initializes the Cognitive Engine.
        Can allow loading from a compiled JSON/CharX path OR a direct Profile object.
        """
        if not self._is_initialized:
            raise RuntimeError("System not initialized. Call initialize_system() first.")

        if profile_obj:
            self.current_profile = profile_obj
        elif output_path:
            # TODO: Implement loading from file using CharXLoader or raw JSON
            # profile_data = ...
            # self.current_profile = CharacterProfile(**profile_data)
            raise NotImplementedError("File loading not yet fully integrated in Controller.")
        else:
            raise ValueError("Must provide either output_path or profile_obj.")

        logger.info(f"CoreController: Loading character '{self.current_profile.name}'...")

        # 4. State Manager
        # Use ID if available, else Name
        char_key = self.current_profile.id if self.current_profile.id else self.current_profile.name
        self.character_manager = CharacterStateManager(char_key)
        
        # 5. Engine
        self.engine = CognitiveEngine(
            llm_client=self.llm_client,
            tool_registry=self.tool_registry,
            profile=self.current_profile,
            config_manager=self.config_manager,
            memory_manager=self.memory_manager,
            character_manager=self.character_manager
        )
        
        # 6. Bind Persistence (History)
        # Assuming char_key is the directory name ID
        from src.foundation.paths.manager import PathManager
        history_path = PathManager.get_instance().get_characters_dir() / char_key / "history.json"
        
        logger.info(f"CoreController: Binding history to {history_path}")
        self.memory_manager.bind_persistence(history_path)
        
        # 7. Session Initialization Logic
        try:
             import time
             is_first_run = self.memory_manager.is_empty()
             
             if is_first_run:
                 # First Run Logic
                 if self.current_profile.first_message:
                     logger.info("CoreController: Inserting First Message.")
                     self.memory_manager.add_interaction("assistant", self.current_profile.first_message)
             else:
                 # Resume Logic
                 last_ts = self.memory_manager.get_last_timestamp()
                 if last_ts > 0:
                     current_ts = time.time()
                     delta_seconds = current_ts - last_ts
                     hours_passed = delta_seconds / 3600.0
                     
                     # Only log if significant time passed (e.g. > 1 minute? Or just always?)
                     # User request: "ユーザーが入室しました　前回の終了（最後の会話履歴）から何時間経ちました"
                     # Let's format nicely.
                     
                     time_str = ""
                     if hours_passed < 1.0:
                         mins = int(delta_seconds / 60)
                         time_str = f"{mins} minutes"
                     else:
                         time_str = f"{hours_passed:.1f} hours"
                         
                     msg = f"User entered the room. {time_str} have passed since the last session."
                     self.memory_manager.add_system_event(msg)
                     logger.info(f"CoreController: Resume Log: {msg}")

        except Exception as e:
            logger.error(f"CoreController: Session Init Error: {e}")
            
        logger.info("CoreController: Engine Ready.")

    async def handle_user_input(self, text: str) -> None:
        """
        Main Loop Entry Point.
        Feeds user input to memory and executes a cognitive cycle.
        """
        if not self.engine:
            raise RuntimeError("Engine not loaded. Load a character first.")
            
        logger.info(f"CoreController: User Input: {text}")
        
        # Delegate to Engine's Autonomous Loop
        await self.engine.start_user_turn(text)

    def get_history(self) -> List[Dict[str, Any]]:
        """Returns visual history."""
        if not self.memory_manager:
            return []
        return self.memory_manager.get_context_history()

    def get_chat_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns visual history safely formatted for UI."""
        if not self.memory_manager:
            return []
        return self.memory_manager.get_history_for_restore(limit)

    def get_status(self) -> Dict[str, Any]:
        """Returns minimal status (Rapport, etc)."""
        if not self.character_manager:
            return {}
        return self.character_manager.get_state().relationship.model_dump()

    async def shutdown(self):
        """Cleanup."""
        if self.local_model_manager:
            self.local_model_manager.stop_server()
        pass

    # --- Local LLM Facade ---
    def get_local_model_presets(self):
        if self.local_model_manager:
            return self.local_model_manager.get_presets()
        return []

    def start_local_llm(self, model_filename: str):
        if self.local_model_manager:
            return self.local_model_manager.launch_server(model_filename)
        return False
        
    def stop_local_llm(self):
        if self.local_model_manager:
            self.local_model_manager.stop_server()

    def download_model(self, repo_id: str, filename: str, callback=None):
        if self.local_model_manager:
            return self.local_model_manager.download_model(repo_id, filename, progress_callback=callback)
        return False

    def get_download_status(self):
        if self.local_model_manager:
            return self.local_model_manager.get_download_status()
        return {}
