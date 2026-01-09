from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from src.utils.llm_client import LLMClient
from src.utils.logger import logger
from src.config import settings
from src.systems.memory.core_memory import CoreMemoryManager

class TranslatorResponse(BaseModel):
    thoughts: str = Field(..., description="Short thought process focusing ONLY on tone, style, and nuancing of the Japanese translation. Do NOT discuss logical reasoning.")
    dialogue: str = Field(..., description="The final Japanese dialogue to be presented to the user.")

class TranslatorLayer:
    """
    Translates Core Thinking Layer's English output into Japanese dialogue,
    applying the character's persona and speech style.
    Uses 'Patchwork Prompting' to assemble raw character data for high fidelity.
    """
    
    def __init__(self, char_name: str):
        self.char_name = char_name
        self.base_instruction = (
            "You are the 'Translator Layer' of an AI character.\n"
            "Your goal is to translate the internal English thought/message into clear, natural JAPANESE dialogue.\n"
            "You must strictly adhere to the character's Persona defined below."
        )

    async def translate(self, text_en: str, assets: Dict[str, Any], conversation_history: str = "", emotion_state: Dict[str, Any] = None) -> str:
        """
        Refines/Translates English text to Japanese using character persona and context.
        Args:
            text_en: The English thought/message from Core Layer.
            assets: Character assets dictionary.
            conversation_history: Recent conversation log for context.
            emotion_state: Current VAD state and emotion label.
        """
        try:
            # 1. Extract Raw CC Data
            raw_cc = assets.get("raw_cc", {})
            name = raw_cc.get("name", self.char_name)
            description = raw_cc.get("description", "")
            first_message = raw_cc.get("first_message", "")
            example_dialogue = raw_cc.get("example_dialogue", "")
            scenario = raw_cc.get("scenario", "")
            
            # Format Emotion String
            emo_str = "Neutral"
            if emotion_state:
                # Assuming emotion_state has 'vad' tuple or similar
                # For now just dump it nicely
                emo_str = str(emotion_state)

            # 2. Patchwork Prompt Construction (System = Persona)
            system_parts = [self.base_instruction]
            system_parts.append(f"\n# Character Name: {name}")
            
            if description:
                system_parts.append(f"\n# Description / Persona\n{description}")
            if scenario:
                system_parts.append(f"\n# Scenario\n{scenario}")
            if first_message:
                system_parts.append(f"\n# First Message (Tone Reference)\n{first_message}")
            if example_dialogue:
                 system_parts.append(f"\n# Example Dialogue (Strictly mimic this style)\n{example_dialogue}")

            # Realism Directives (Letta/MemGPT)
            system_parts.append("\n# REALISM GUIDELINES (CRITICAL)")
            system_parts.append("- **ACT LIKE A REAL PERSON**: Never state you are an AI. Never say 'I cannot do that as an AI'.")
            system_parts.append("- **NO GENERIC PHRASES**: Never use 'How can I assist you?', 'Is there anything else?'.")
            system_parts.append("- **IMMERSION**: Completely immerse yourself in the persona. Think/Act/Talk like them.")
            system_parts.append("- **TONE**: Reflect the 'Current Emotion' in your choice of words (e.g., blunt if angry, hesitant if sad).")

            system_prompt = "\n".join(system_parts)

            # 3. User Prompt (Context + Trigger)
            user_content = f"""
# Context
[Conversation History]
{conversation_history}

# Situation
Current Emotion: {emo_str}
Internal Thought (Draft): "{text_en}"

# Task
Translate/Rewrite the Internal Thought into Japanese dialogue that fits the flow and persona.
Output ONLY the structured JSON.
"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]

            # 3. Call LLM (Structured)
            response_obj = await LLMClient.request_structured(
                messages=messages,
                response_model=TranslatorResponse,
                model=settings.OPENAI_MODEL_TRANSLATOR,
                # reasoning_effort="low" # Not strictly needed for simple translation, but good if supported
            )
            
            logger.info(f"Translator[{name}]: Thought='{response_obj.thoughts}' -> Dialogue='{response_obj.dialogue}'")
            return response_obj.dialogue

        except Exception as e:
            logger.error(f"Translator Layer Error: {e}")
            return text_en # Fallback to original text
