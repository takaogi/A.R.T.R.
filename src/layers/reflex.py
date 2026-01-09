from typing import List
from src.utils.llm_client import LLMClient
from src.utils.logger import logger
from src.utils.path_helper import get_resource_path
from src.config import settings
from src.systems.memory.core_memory import CoreMemoryManager
from src.systems.memory.conversation import ConversationManager

class ReflexLayer:
    def __init__(self):
        self.char_name = None
        self.base_system_prompt = "Using default Reflex prompt."
        self.core_memory = None
        self.conversation = None
        self.initialized = False

    def load_character(self, char_name: str):
        """
        Initializes the layer for a specific character.
        """
        self.char_name = char_name
        self.system_prompt_path = get_resource_path("src/templates/system_reflex.md")
        self.base_system_prompt = self._load_system_prompt()
        
        # Initialize Memories
        self.core_memory = CoreMemoryManager(char_name)
        self.conversation = ConversationManager(char_name)
        self.initialized = True
        logger.info(f"ReflexLayer initialized for '{char_name}'.")

    def _load_system_prompt(self) -> str:
        try:
            if self.system_prompt_path.exists():
                return self.system_prompt_path.read_text(encoding="utf-8")
            else:
                return "You are A.R.T.R. Reflex Layer. Respond concisely in Japanese."
        except Exception as e:
            logger.error(f"Failed to load reflex system prompt: {e}")
            return "You are A.R.T.R. Reflex Layer."

    def _build_system_prompt(self) -> str:
        """Construct the full system prompt with Core Memory."""
        if not self.initialized:
            return "Reflex Layer not initialized."
            
        prompt = self.base_system_prompt + "\n\n"
        prompt += "## Core Memory\n"
        if self.core_memory:
             prompt += self.core_memory.render_xml()
        return prompt

    async def process_input(self, user_input: str, history: List[dict] = None) -> str:
        """
        Processes user input through the Reflex Layer (Fast/Local).
        """
        # 1. Update Conversation History (User)
        self.conversation.add_message("user", user_input)
        
        # 2. Build Context
        # Load recent history (e.g., last 10 messages)
        # We transform conversation history to OpenAI message format
        # Note: 'history' arg is kept for compatibility but we prefer using ConversationManager
        
        full_system_prompt = self._build_system_prompt()
        
        recent_msgs_data = self.conversation.get_history(limit=10)
        recent_msgs = []
        for msg in recent_msgs_data:
            # Skip the just added user message if it's already in history? 
            # get_history returns it. So we should be careful not to double add if we pass it explicitly.
            # But here we are building the full list for the LLM.
            
            # Map 'user'/'assistant' roles. Our ConversationManager uses 'user'/'assistant' (or whatever passed).
            # If role is 'reflex' or something else, map to 'assistant'.
            role = msg['role']
            if role not in ('user', 'system'):
                role = 'assistant'
            recent_msgs.append({"role": role, "content": msg['content']})

        # The last message in recent_msgs is the user input we just added.
        # But we shouldn't duplicate it if we appended it to history.
        # Wait, get_history includes the one we just added.
        # So messages list should be:
        # System + History (which includes latest User message)
        
        messages = [
            {"role": "system", "content": full_system_prompt},
            *recent_msgs 
        ]

        try:
            # Reflex uses the 'Text' request method (Local/Fast)
            response = await LLMClient.request_text(
                messages=messages,
                model=settings.OPENAI_MODEL_REFLEX,
                reasoning_effort=settings.REASONING_EFFORT_REFLEX
            )
            
            # 3. Update Conversation History (Bot)
            self.conversation.add_message("assistant", response)
            
            return response
        except Exception as e:
            logger.error(f"Reflex Layer Error: {e}")
            return "..." # Fallback response if everything fails

reflex_layer = ReflexLayer()
