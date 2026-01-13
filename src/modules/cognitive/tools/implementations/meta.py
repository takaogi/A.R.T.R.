from typing import Any
from src.modules.llm_client.prompts.cognitive.actions import UpdateCoreMemoryAction
from ..interface import BaseTool
from src.foundation.logging import logger

class UpdateCoreMemoryTool(BaseTool[UpdateCoreMemoryAction]):
    def __init__(self):
        self.state_manager = None

    def set_manager(self, manager: Any):
        self.state_manager = manager

    async def execute(self, action: UpdateCoreMemoryAction):
        if not self.state_manager:
            return {"status": "error", "message": "State Manager not available"}

        logger.info(f"[CORE_UPDATE] Section={action.section} Target='{action.target_content}' New='{action.content}'")
        
        # Helper for strict replacement
        def strict_replace(text: str, target: str, replacement: str):
            if not target:
                return text + "\n" + replacement, "Appended"
            
            count = text.count(target)
            if count == 0:
                return None, "Target not found"
            if count > 1:
                return None, "Multiple matches found"
            
            return text.replace(target, replacement), "Replaced"

        # 1. User Info (stored in CharacterState)
        if action.section == "user_info":
            current_state = self.state_manager.get_state()
            current_info = current_state.user_profile
            
            new_info, msg = strict_replace(current_info, action.target_content, action.content)
            
            if new_info is None:
                 if msg == "Multiple matches found":
                     return {"status": "error", "message": f"Error: Target '{action.target_content}' found multiple times in User Info. Please be more specific."}
                 else: # Target not found -> Append as fallback (or should we error? User request implies strictness for replacement, but appending is useful. Let's stick to append fallback for 'not found', error for 'multiple')
                     # Re-evaluating: User asked for "Check if multiple found -> Error". 
                     # They didn't explicitly remove the "Append if not found" logic, but standard edit logic usually suggests append if empty target.
                     # If target is provided but NOT found, it's safer to Append (as per previous logic) OR Error.
                     # Previous logic: "Target content not found... Appending instead".
                     # I will keep the "Append if not found" behavior for robustness, but enforce the "Error if Multiple".
                     logger.warning("[CORE_UPDATE] Target content not found in User Info. Appending instead.")
                     new_info = f"{current_info}\n{action.content}"
            
            # Update State
            self.state_manager.update_user_profile(new_info)
            return {"status": "success", "message": "User Info Updated."}

        # 2. Character Profile
        card = getattr(self.state_manager, "card", None)
        profile = None
        if card:
            profile = card.profile
        elif hasattr(self.state_manager, "profile"):
            profile = self.state_manager.profile
            
        if not profile:
             return {"status": "error", "message": "Character Profile not accessible via Manager."}

        # Helper for profile field update
        def update_profile_field(field_name: str, target: str, content: str, label: str):
            current_val = getattr(profile, field_name, "")
            new_val, msg = strict_replace(current_val, target, content)
            
            if msg == "Multiple matches found":
                 return {"status": "error", "message": f"Error: Target '{target}' found multiple times in {label}."}
            
            if new_val is None: # Not found -> Append
                 if current_val:
                    new_val = f"{current_val}\n{content}"
                 else:
                    new_val = content
            
            setattr(profile, field_name, new_val)
            self.state_manager.save_card()
            return {"status": "success", "message": f"{label} Updated."}

        # Handle Overview (Description)
        if action.section == "overview":
            return update_profile_field("description", action.target_content, action.content, "Overview")

        # Handle Appearance
        if action.section == "appearance":
             return update_profile_field("appearance", action.target_content, action.content, "Appearance")

        # Handle Personality (Surface/Inner Persona)
        if action.section == "personality":
            # Search in Surface
            if action.target_content and action.target_content in profile.surface_persona:
                new_surface, msg = strict_replace(profile.surface_persona, action.target_content, action.content)
                if msg == "Multiple matches found":
                     return {"status": "error", "message": f"Error: Target '{action.target_content}' found multiple times in Surface Persona."}
                
                profile.surface_persona = new_surface
                self.state_manager.save_card()
                return {"status": "success", "message": "Surface Persona Updated."}
            
            # Search in Inner
            if action.target_content and action.target_content in profile.inner_persona:
                new_inner, msg = strict_replace(profile.inner_persona, action.target_content, action.content)
                if msg == "Multiple matches found":
                     return {"status": "error", "message": f"Error: Target '{action.target_content}' found multiple times in Inner Persona."}

                profile.inner_persona = new_inner
                self.state_manager.save_card()
                return {"status": "success", "message": "Inner Persona Updated."}
            
            # If not found in either -> Append to Inner
            if profile.inner_persona:
                profile.inner_persona += f"\n{action.content}"
            else:
                profile.inner_persona = action.content
                
            self.state_manager.save_card()
            return {"status": "success", "message": "Inner Persona Updated (Appended)."}

        # Handle Scenario
        if action.section == "scenario":
             return update_profile_field("initial_situation", action.target_content, action.content, "Scenario")

        return {"status": "error", "message": f"Section '{action.section}' not handled."}

