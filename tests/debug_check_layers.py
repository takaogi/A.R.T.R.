import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.systems.personality.manager import PersonalityManager
from src.layers.preprocessing import PreProcessor
from src.utils.logger import logger

def main():
    logger.info("--- Starting Layer Verification ---")
    
    # 1. Personality Generation
    pm = PersonalityManager()
    # Create dummy character if not exists
    char_name = "DebugChar"
    char_path = pm.get_character_path(char_name)
    if not char_path.exists():
        logger.info("Creating dummy character...")
        char_path.parent.mkdir(parents=True, exist_ok=True)
        import json
        dummy_data = {
            "name": char_name,
            "description": "A test character. Very energetic and loud.",
            "first_message": "HELLO WORLD!",
            "personality": "Energetic, Loud, Tech-savvy",
            "reflex_examples": "Yeah!\nNo way!\nCool!",
            "system_prompt": "",
            "white_room_path": "data/white_room",
            "example_dialogue": "<START>\n{{user}}: Hi\n{{char}}: HELLO!"
        }
        with open(char_path, "w", encoding="utf-8") as f:
            json.dump(dummy_data, f, ensure_ascii=False)
            
    logger.info(f"Loading character: {char_name}")
    assets = pm.load_character(char_name)
    
    if assets:
        logger.success("Assets generated/loaded successfully!")
        logger.info(f"Reflex Keys: {assets.get('reflex_memory', {}).keys()}")
        logger.info(f"Core Memory Length: {len(assets.get('core_memory', ''))}")
        # logger.info(f"Params: {assets.get('system_params', {})}")
        # logger.info(f"Styles: {assets.get('reaction_styles', {})}")
    else:
        logger.error("Failed to load assets.")
        return

    from src.systems.memory.archival_memory import ArchivalMemory

    # 1.5 Initialize Memory
    archival_memory = ArchivalMemory(char_name)

    # 2. Pre-processing
    logger.info("\n--- Testing PreProcessor ---")
    # Initialize PreProcessor with archival_memory
    pp = PreProcessor(archival_memory)
    
    # Mock/Seed Memories
    logger.info("Seeding memories...")
    pp.archival_association.add_memory("今日の天気は晴れです。", {"tag": "weather"})
    pp.archival_association.add_memory("ユーザーはリンゴが好きだと言っていた。", {"tag": "preference"})
    pp.archival_association.add_memory("秘密の合言葉は『山川』です。", {"tag": "secret"})

    test_inputs = [
        "すごいね！", # Praise
        "リンゴ", # Substring match for Mock Mode
        "合言葉", # Substring match for Mock Mode
    ]
    
    # Mock Consolidation
    logger.info("\n--- Testing Contextual Eviction (Consolidation) ---")
    
    # Existing pool (e.g. from previous turn)
    current_pool = [
        {"memory": {"text": "ユーザーはリンゴが好きだと言っていた。", "embedding": []}, "score": 0.5},
        {"memory": {"text": "秘密の合言葉は『山川』です。", "embedding": []}, "score": 0.5},
    ]
    
    # New findings (e.g. from current turn's association)
    new_findings = [
        {"memory": {"text": "みかんも好きらしい。", "embedding": []}, "score": 0.8}, 
    ]
    
    # Context: Talking about fruits (using keyword 'リンゴ' for mock match)
    context = "リンゴの話"
    
    consolidated = pp.archival_association.consolidate(current_pool, new_findings, context, limit=2)
    
    logger.info(f"Context: {context}")
    for i, m in enumerate(consolidated):
        mem_text = m['memory']['text']
        score = m['score']
        logger.info(f"Top {i+1}: {mem_text} (Score: {score:.2f})")
    
    current_styles = assets.get('reaction_styles', {})
    
    for txt in test_inputs:
        logger.info(f"\nUser Input: '{txt}'")
        res = pp.process(txt, current_styles)
        # Inject Style based on map
        cat = res['analysis']['category']
        # The key should exist if generated correctly, or default
        style = current_styles.get(cat, 'Unknown')
        logger.info(f"Detected Category: {cat}")
        logger.info(f"Selected Style (Granular): {style}")
        logger.info(f"Meta Injection:\n{res['meta_injection'].strip()}")

if __name__ == "__main__":
    main()
