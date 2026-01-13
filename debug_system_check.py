import sys
import os
import asyncio

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.core.controller import CoreController
from src.modules.character.schema import CharacterProfile

async def main():
    print("=== A.R.T.R. System Debug (Via CoreController) ===")
    
    # 1. Initialize Controller
    controller = CoreController()
    await controller.initialize_system()
    
    # 2. Dummy Character Profile
    dummy_profile = CharacterProfile(
        name="Debug-Chan",
        description="A debugging assistant focused on verification.",
        personality="Analytical, helpful, precise.",
        first_message="System check initiated.",
        scenario="Debug mode active.",
        mes_example=""
    )
    
    # 3. Load Character
    await controller.load_character(profile_obj=dummy_profile)
    
    # 4. Simulate Input
    user_input = "こんにちは、調子はどうだい？"
    print(f"\n[User Input] {user_input}")
    
    # 5. Handle Input
    response = await controller.handle_user_input(user_input)
    
    if response:
        print("\n=== [Response] ===")
        print(f"Thought: {response.thought}")
        print(f"Expr: {response.show_expression}")
        print(f"Actions: {response.actions}")
        
        # Check History
        print("\n[History Check]")
        history = controller.get_history()
        print(f"Total History Items: {len(history)}")
        for item in history[-2:]:
            print(f"- {item['role']}: {item['content']}")
            
    else:
        print("[ERROR] No response received.")

if __name__ == "__main__":
    asyncio.run(main())
