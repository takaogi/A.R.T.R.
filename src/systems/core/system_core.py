import asyncio
from typing import Dict, List, Any
from src.utils.logger import logger

from src.systems.personality.manager import PersonalityManager
from src.layers.preprocessing import PreProcessor
from src.systems.memory.core_memory import CoreMemoryManager
from src.systems.memory.archival_memory import ArchivalMemory
from src.systems.memory.conversation import ConversationManager
from src.systems.emotion.engine import VADEngine

from src.systems.core.tools.dispatcher import ToolDispatcher
from src.systems.core.prompt_builder import PromptBuilder
from src.systems.core.reasoning_loop import ReasoningLoop

from src.systems.emotion.affection import AffectionManager

from src.systems.attention.manager import AttentionManager
from src.layers.reflex import reflex_layer
from src.layers.translator import TranslatorLayer

class SystemCore:
    """
    Main Facade for the A.R.T.R. Core Thinking Layer.
    Coordinates all subsystems: Perception, Memory, Reasoning, Action.
    """

    def __init__(self, char_name: str, progress_callback=None):
        self.char_name = char_name
        logger.info(f"Initializing SystemCore for '{char_name}'...")
        if progress_callback: progress_callback(f"SystemCore: Initializing for {char_name}...")
        
        # 1. Personality & Configuration
        self.personality_manager = PersonalityManager()
        self.assets = self.personality_manager.load_character(char_name, progress_callback)
        
        # 2. Memory Systems
        if progress_callback: progress_callback("SystemCore: Loading Memories...")
        self.core_memory = CoreMemoryManager(char_name)
        self.archival_memory = ArchivalMemory(char_name)
        self.conversation = ConversationManager(char_name)
        
        # 3. Emotion System
        if progress_callback: progress_callback("SystemCore: Initializing Emotion Engine...")
        system_params = self.assets.get("system_params", {})
        
        # Initialize VAD Engine (Dual Layer)
        self.emotion_engine = VADEngine(char_name, config=system_params)
        
        # Initialize Affection Manager
        self.affection_manager = AffectionManager(char_name)
        
        # Initialize Attention Manager
        self.attention_manager = AttentionManager()

        # Initialize Translator Layer
        self.translator_layer = TranslatorLayer(char_name)

        # Ensure Reflex Layer is ready (it shares state but better safe)
        if not reflex_layer.initialized:
            reflex_layer.load_character(char_name)
        
        # Pacemaker Config (Future Integration)
        self.pacemaker_config = system_params.get("pacemaker", {})
        logger.info(f"Pacemaker Config Loaded: {self.pacemaker_config}") 
        
        # 4. Perception Layer
        if progress_callback: progress_callback("SystemCore: Initializing Perception Layer (E5 Loading)...")
        self.preprocessor = PreProcessor(self.archival_memory)
        
        # 5. Tools & Reasoning
        if progress_callback: progress_callback("SystemCore: Setting up Reasoning Tools...")
        self.dispatcher = ToolDispatcher(
            core_memory=self.core_memory,
            archival_memory=self.archival_memory,
            conversation=self.conversation,
            emotion_callback=self.on_emotion_update,
            affection_callback=self.on_affection_update
        )
        
        self.prompt_builder = PromptBuilder(self.core_memory)
        self.reasoning_loop = ReasoningLoop(self.dispatcher, self.prompt_builder)
        
        logger.info("SystemCore Initialized.")

    # --- Callbacks ---
    def on_emotion_update(self, v, a, d, reason):
        logger.info(f"Emotion CB: {v},{a},{d} ({reason})")
        self.emotion_engine.update(v, a, d)

    def on_affection_update(self, delta, reason):
        logger.info(f"Affection CB: {delta} ({reason})")
        self.affection_manager.update(delta, reason)

    # --- Main Pipeline ---
    async def process_input(self, user_input: str, enable_association: bool = False) -> List[str]:
        """
        Main interaction pipeline.
        User Input -> Attention Check -> (Reflex | Core)
        """
        logger.info(f"Processing input: {user_input} (Assoc: {enable_association})")
        
        # 0. Attention Routing
        is_attentive = self.attention_manager.is_attentive()
        current_attn = self.attention_manager.get_value()
        logger.info(f"Current Attention: {current_attn:.2f} (Attentive: {is_attentive})")
        
        # If LOW Attention -> Reflex Mode (DEBUG: DISABLED to force Core)
        if False: # not is_attentive:
            logger.info("Attention LOW. Routing to Reflex Layer.")
            # Boost Attention (Waking up for next turn)
            self.attention_manager.boost()
            
            # Execute Reflex
            reflex_response = await reflex_layer.process_input(user_input)
            
            # In future: Route to Translator/UI asynchronously if needed.
            # Currently returns result directly.
            return [reflex_response]

        # If HIGH Attention -> Core Logic
        logger.info("Attention HIGH. Proceeding to Core Thinking.")
        self.attention_manager.boost() # Maintain attention
        
        # 1. Pre-processing
        reaction_styles = self.assets.get("reaction_styles", {}) if self.assets else {}
        pre_process_data = self.preprocessor.process(user_input, reaction_styles, enable_association=enable_association)
        
        # 2. Reasoning Loop (Returns list of English Content)
        # We assume ReasoningLoop returns [ "Hello.", "I am fine." ]
        raw_responses_en = await self.reasoning_loop.execute(
            user_input=user_input, 
            conversation_manager=self.conversation,
            pre_process_data=pre_process_data,
            associated_memories=pre_process_data.get("associations", [])
        )
        
        # 3. Translation (English -> Japanese)
        translated_responses = []
        for text_en in raw_responses_en:
            # Pass full assets (including raw_cc) to Translator
            text_ja = await self.translator_layer.translate(text_en, self.assets)
            translated_responses.append(text_ja)
            
            # Update Conversation History with FINAL Japanese output
            # ReasoningLoop adds "assistant" messages with JSON dump (Action + Thought).
            # But the 'visible' dialogue history should probably contain the Japanese text?
            # Actually, `ReasoningLoop` adds to history for *Context* during the loop.
            # But for the UI and long-term history, we might want the Japanese version.
            # However, ConversationManager history is shared.
            # Let's trust ReasoningLoop's internal history for reasoning, 
            # and append the final Japanese text as what the user sees/response?
            # No, if ReasoningLoop adds it, it's already there.
            # Wait, ReasoningLoop adds the *JSON* response provided by LLM.
            # We might want to inject the "Translated" content as what was actually 'said'.
            # For now, let's just return the translated string to UI.
            # The UI will display it.
            # We typically log the final clean conversation.
            # Let's add the Japanese response to conversation manager as a clean 'text' entry if needed,
            # or rely on the JSON one being sufficient for context.
            # User wants "UI to display it". Returning list is enough for UI.
            
        return translated_responses


    def trigger_random_recall(self, count: int = 1) -> List[str]:
        """
        Force a random memory recall.
        Useful for "spontaneous thought" or "wandering mind".
        """
        # Feature not yet in ArchivalMemory, but stubbing the interface on SystemCore
        # memories = self.archival_memory.get_random(count)
        # For now, return empty or implement later.
        logger.info(f"Trigger Random Recall (Count: {count}) - Stub")
        return []
