from typing import List, Optional
from pydantic import BaseModel, Field


class GeneratedProfile(BaseModel):
    """
    Structure for LLM to generate character profile data.
    This schema defines the 'Ideal A.R.T.R. Format'.
    """
    model_config = {"extra": "forbid"}
    
    # Identity
    name: str = Field(..., description="Character Name (Japanese preferred).")
    aliases: List[str] = Field(..., description="List of nicknames or aliases. \n(例: ['ミサ', '委員長'])")
    appearance: str = Field(..., description="Visual description (Hair, eyes, clothing, etc.). \n(例: '銀髪のロングヘア、紅い瞳、白いワンピース')")
    description: str = Field(..., description="Brief concept or summary of the character. \n(例: 'ツンデレな幼馴染。実は主人公のことが好きだが素直になれない。')")

    # Persona (Multi-dimensional)
    surface_persona: str = Field(..., description="【Outward Persona / Behavior】\nHow the character behaves towards others. Speech tone, attitude, social conduct. \n(例: '礼儀正しく振る舞うが、どこか他者を突き放したような冷たさがある。誰に対しても敬語を使う。')")
    inner_persona: str = Field(..., description="【Inner Persona / Thoughts】\nInternal monologues, private feelings, and underlying motives. \n(例: '実は極度の寂しがり屋だが、プライドが邪魔して素直になれない。過去のトラウマから他人に依存することを恐れている。')")
    speech_patterns: List[str] = Field(..., description="【Speech Patterns】\nSpecific rules for speech. Pronouns, sentence endings, quirks. **Ensure these are detailed enough to perfectly replicate the character's tone.** \n(例: ['一人称は「私」', '語尾に「〜だわ」をつける', '興奮すると早口になる'])")
    
    # Narrative
    background_story: str = Field(..., description="Backstory, history, important past events. Bullet points recommended.")
    world_definition: str = Field(..., description="【World Setting】\nStatic rules, magic systems, geography, organizations. \n(例: '魔法が科学として体系化された現代ファンタジー世界。魔力は血統によって決まる。')")
    
    # Optional Context (Leave empty if not found)
    # Strict compliance: Field(..., description=...) means key is required, type includes null
    initial_situation: Optional[str] = Field(..., description="【Initial Situation】\nContext at start. Location, time, relationship. LEAVE EMPTY (Null) if not present in source. \n(例: '放課後の教室。二人きり。ユーザーは彼女に呼び出された生徒。')")
    first_message: Optional[str] = Field(..., description="【First Message】\nOpening line displayed to the user. This can be pure dialogue, or a narrative introduction (scene setup, story opening). LEAVE EMPTY (Null) if not present in source. \n(例: '……遅かったじゃない。' や、情景描写を含む導入文)")
    
    # Examples
    speech_examples: List[str] = Field(..., description="【Speech Examples】\nList of actual character quotes. Extract ONLY the character's lines. \n(例: ['あら、ごきげんよう。', '貴様になど興味はないわ。', 'ふふ、面白いことを言うのね。'])")
