from typing import Dict, List, Optional, Tuple
from src.systems.emotion.analyzer import EmotionAnalyzer
from src.systems.memory.archival_memory import ArchivalMemory
from src.systems.memory.archival_association import ArchivalAssociation
from src.config.reaction_styles import REACTION_STYLE_DB
from src.utils.logger import logger

class PreProcessor:
    """
    Handles input analysis, habituation control, and metadata injection.
    """
    def __init__(self, archival_memory: ArchivalMemory):
        self.emotion_analyzer = EmotionAnalyzer() # Singleton access
        self.archival_association = ArchivalAssociation(archival_memory)
        self.habituation_history: List[Dict] = []
        self.habituation_window = 180.0 # seconds
        self.decay_factors = [1.0, 0.5, 0.25, 0.0]

    def process(self, user_text: str, reaction_styles: Dict[str, str], enable_association: bool = True) -> Dict:
        """
        Analyzes text and returns metadata for injection.
        
        Args:
            user_text: Raw user input.
            reaction_styles: Map of {Anchor: StyleName} from Personality.
            enable_association: Whether to trigger memory recall.
        """
        # 1. Emotion Analysis
        analysis = self.emotion_analyzer.analyze(user_text)
        category = analysis["category"]
        confidence = analysis["confidence"]
        intensity = analysis["intensity"]

        # 2. Association System (Memory Recall from Wrapper)
        associated_memories = []
        if enable_association:
            associated_memories = self.archival_association.associate(user_text, top_k=3)
        
        # 3. Habituation Control
        effect_multiplier = self._check_habituation(category)
        final_intensity = intensity * effect_multiplier
        
        is_habituated = effect_multiplier < 0.1

        # 4. VAD Delta Calculation
        selected_style_name = reaction_styles.get(category)
        
        vad_delta = (0.0, 0.0, 0.0)
        start_vad_desc = ""
        
        if selected_style_name and selected_style_name in REACTION_STYLE_DB:
            style_def = REACTION_STYLE_DB[selected_style_name]
            base_delta = style_def.vad_delta
            # Formula: (Style_VAD * Intensity) / 5.0
            vad_delta = tuple((v * final_intensity) / 5.0 for v in base_delta)
            start_vad_desc = f"Style: {selected_style_name} ({style_def.description})"
        else:
            start_vad_desc = f"Style: {selected_style_name} (Unknown)"
        
        logger.info(f"PreProcess: {category} (Int:{intensity:.2f} -> {final_intensity:.2f}) -> VAD Delta:{vad_delta}")
        if associated_memories:
            logger.info(f"Associated {len(associated_memories)} memories.")

        return {
            "analysis": analysis,
            "associated_memories": associated_memories,
            "meta_injection": self._format_injection(analysis, effect_multiplier, final_intensity, start_vad_desc, vad_delta, associated_memories),
            "is_habituated": is_habituated,
            "final_intensity": final_intensity,
            "vad_delta": vad_delta
        }

    def _check_habituation(self, category: str) -> float:
        import time
        now = time.time()
        # Clean history
        self.habituation_history = [h for h in self.habituation_history if now - h["time"] < self.habituation_window]
        
        # Count occurences
        count = sum(1 for h in self.habituation_history if h["category"] == category)
        
        factor = 0.0
        if count < len(self.decay_factors):
            factor = self.decay_factors[count]
        else:
            factor = 0.0
            
        # Append new event
        self.habituation_history.append({"category": category, "time": now})
        
        return factor

    def _format_injection(self, analysis: Dict, multiplier: float, final_intensity: float, style_desc: str, vad_delta: Tuple[float, float, float], memories: List[Dict]) -> str:
        # Construct the injection string for the prompt
        v, a, d = vad_delta
        
        mem_str = ""
        if memories:
            mem_str = "\n[Associated Memories]\n"
            for m in memories:
                # m is {memory: {...}, score: float}
                mem_data = m["memory"]
                score = m["score"]
                mem_str += f"- (Sim:{score:.2f}) {mem_data['text']}\n"
        
        return f"""
[Intuition Logic]
Detected Intent: {analysis['category']} (Confidence: {analysis['confidence']:.1f}%)
Habituation: {multiplier*100:.0f}% Effectiveness
Output Intensity: {final_intensity:.2f}
Reaction: {style_desc}
Emotional Shift: V{v:+.2f}/A{a:+.2f}/D{d:+.2f}{mem_str}
"""
