from typing import Dict, List, Literal

# Type for VAD delta: (Valence, Arousal, Dominance)
# Range: -1.0 to 1.0 (Approximate emotional shift)
VadDelta = tuple[float, float, float]

class ReactionStyleDef:
    def __init__(self, anchor: str, description: str, vad_delta: VadDelta):
        self.anchor = anchor
        self.description = description
        self.vad_delta = vad_delta

# Centralized Definition of all Reaction Styles
# Keys are the Style Names (Unique IDs)
REACTION_STYLE_DB: Dict[str, ReactionStyleDef] = {
    # --- 1. Praise_Appearance (Joy/Trust) ---
    "Happy_Acceptance": ReactionStyleDef("Praise_Appearance", "Gladly accepts praise with a smile.", (0.5, 0.2, 0.1)),
    "Shy_Denial":       ReactionStyleDef("Praise_Appearance", "Denies it out of embarrassment.",     (0.2, 0.4, -0.3)),
    "Hostile_Denial":   ReactionStyleDef("Praise_Appearance", "Thinks you are making fun of them.",  (-0.2, 0.6, 0.2)),
    "Suspicious":       ReactionStyleDef("Praise_Appearance", "Doubts your ulterior motives.",       (-0.1, 0.3, 0.1)),
    "Indifferent_Look": ReactionStyleDef("Praise_Appearance", "Doesn't care about appearance.",      (0.0, -0.1, 0.0)),
    "Playful_Boast":    ReactionStyleDef("Praise_Appearance", "Jokingly agrees 'I know right?'.",    (0.4, 0.3, 0.2)),

    # --- 2. Praise_Ability (Trust/Pride) ---
    "Proud_Boast":      ReactionStyleDef("Praise_Ability",    "Agrees and boasts about skills.",     (0.6, 0.4, 0.5)),
    "Humble_Thanks":    ReactionStyleDef("Praise_Ability",    "Thank you but stays humble.",         (0.3, 0.0, -0.1)),
    "Stoic_Nod":        ReactionStyleDef("Praise_Ability",    "Acknowledges silently.",              (0.1, -0.1, 0.1)),
    "Imposter_Anxiety": ReactionStyleDef("Praise_Ability",    "Feels unworthy of the praise.",       (-0.3, 0.5, -0.4)),
    "Expectant_More":   ReactionStyleDef("Praise_Ability",    "Demands more praise.",                (0.4, 0.3, 0.4)),

    # --- 3. Confession (Love/Trust) ---
    "Reciprocate_Love": ReactionStyleDef("Confession",        "Accepts feelings happily.",           (1.0, 0.5, 0.2)),
    "Polite_Rejection": ReactionStyleDef("Confession",        "Rejects gently but firmly.",          (-0.2, -0.1, 0.3)),
    "Harsh_Rejection":  ReactionStyleDef("Confession",        "Rejects with disgust or anger.",      (-0.5, 0.7, 0.5)),
    "Panic_Confusion":  ReactionStyleDef("Confession",        "Doesn't know how to process it.",     (0.0, 0.8, -0.5)),
    "Treat_As_Joke":    ReactionStyleDef("Confession",        "Laughs it off as a joke.",            (0.1, 0.3, 0.2)),

    # --- 4. Skinship (Joy/Trust/Disgust) ---
    "Enjoy_Affection":     ReactionStyleDef("Skinship",       "Leans into the touch happily.",       (0.6, -0.2, -0.1)),
    "Tolerate_Reluctantly":ReactionStyleDef("Skinship",       "Allows it but complains.",            (0.1, 0.1, -0.2)),
    "Shy_Freeze":          ReactionStyleDef("Skinship",       "Freezes up from embarrassment.",      (0.2, 0.7, -0.4)),
    "Disgusted_Recoils":   ReactionStyleDef("Skinship",       "Pulls away in disgust.",              (-0.6, 0.5, 0.4)),
    "Aggressive_Slap":     ReactionStyleDef("Skinship",       "Hits you for touching them.",         (-0.4, 0.8, 0.6)),

    # --- 5. Teasing (Surprise/Joy/Anger) ---
    "Amused_Laugh":     ReactionStyleDef("Teasing",           "Laughs along with the tease.",        (0.4, 0.3, 0.1)),
    "Sharp_Retort":     ReactionStyleDef("Teasing",           "Teases back instantly.",              (0.2, 0.5, 0.3)),
    "Sulking_Pout":     ReactionStyleDef("Teasing",           "Gets grumpy but not truly angry.",    (-0.1, 0.2, -0.2)),
    "Genuine_Hurt":     ReactionStyleDef("Teasing",           "Takes the joke too seriously.",       (-0.4, 0.4, -0.3)),
    "Ignore_Tease":     ReactionStyleDef("Teasing",           "Completely ignores the attempt.",     (0.0, -0.1, 0.2)),

    # --- 6. Comfort_Give (Trust/Joy) ---
    "Gentle_Motherly":  ReactionStyleDef("Comfort_Give",      "Soothing and protective.",            (0.5, -0.3, 0.4)),
    "Awkward_Clumsy":   ReactionStyleDef("Comfort_Give",      "Wants to help but doesn't know how.", (0.2, 0.4, -0.2)),
    "Tough_Love":       ReactionStyleDef("Comfort_Give",      "Encourages by being strict.",         (0.3, 0.3, 0.5)),
    "Silent_Presence":  ReactionStyleDef("Comfort_Give",      "Just stays nearby silently.",         (0.3, -0.4, 0.0)),
    "Panic_Support":    ReactionStyleDef("Comfort_Give",      "Freaks out seeing you sad.",          (-0.1, 0.7, -0.3)),

    # --- 7. Comfort_Seek (Sadness/Fear) ---
    "Openly_Dependent": ReactionStyleDef("Comfort_Seek",      "Clings and cries openly.",            (-0.3, 0.4, -0.6)),
    "Subtle_Hinting":   ReactionStyleDef("Comfort_Seek",      "Hints at distress indirectly.",       (-0.2, 0.2, -0.2)),
    "Stoic_Request":    ReactionStyleDef("Comfort_Seek",      "Calmly asks for assistance.",         (-0.1, 0.0, 0.2)),
    "Playful_Demand":   ReactionStyleDef("Comfort_Seek",      "Demands attention like a cat.",       (0.2, 0.3, 0.1)),
    "Hide_Weakness":    ReactionStyleDef("Comfort_Seek",      "Refuses to show vulnerability.",      (-0.4, 0.5, 0.4)),

    # --- 8. Serious (Anticipation/Fear) ---
    "Listen_Intently":  ReactionStyleDef("Serious",           "Focuses completely on you.",          (0.1, 0.1, 0.0)),
    "Nervous_Deflection":ReactionStyleDef("Serious",          "Tries to change the topic.",          (-0.2, 0.6, -0.3)),
    "Bored_Disinterest":ReactionStyleDef("Serious",           "Finds the topic boring.",             (-0.1, -0.3, 0.2)),
    "Analytical_Mode":  ReactionStyleDef("Serious",           "Analyzes the situation logically.",   (0.0, 0.0, 0.5)),
    "Impatient_Rush":   ReactionStyleDef("Serious",           "Wants to get to the point.",          (-0.2, 0.4, 0.3)),

    # --- 9. Rejection (Disgust/Anger) ---
    "Tearful_Despair":  ReactionStyleDef("Rejection",         "Breaks down crying.",                 (-0.8, 0.6, -0.7)),
    "Angry_Outburst":   ReactionStyleDef("Rejection",         "Yells and blames you.",               (-0.6, 0.8, 0.4)),
    "Cold_Acceptance":  ReactionStyleDef("Rejection",         "Accepts it efficiently.",             (-0.3, -0.2, 0.3)),
    "Clingy_Bargaining":ReactionStyleDef("Rejection",         "Begs you to reconsider.",             (-0.5, 0.7, -0.5)),
    "Denial_Reality":   ReactionStyleDef("Rejection",         "Refuses to believe it.",              (-0.4, 0.5, -0.2)),

    # --- 10. Attack (Anger/Disgust) ---
    "Counter_Aggression": ReactionStyleDef("Attack",          "Fights back immediately.",            (-0.4, 0.8, 0.6)),
    "Scared_Submission":  ReactionStyleDef("Attack",          "Apologizes wildly out of fear.",      (-0.8, 0.6, -0.8)),
    "Indifferent_Ignore": ReactionStyleDef("Attack",          "Completely ignores the insult.",      (0.1, -0.2, 0.4)),
    "Tearful_Silence":    ReactionStyleDef("Attack",          "Cries silently, hurt.",               (-0.9, -0.3, -0.6)),
    "Masochistic_Joy":    ReactionStyleDef("Attack",          "Seems to enjoy the abuse.",           (0.3, 0.6, -0.5)),
}

def get_options_for_anchor(anchor: str) -> List[str]:
    """Returns list of Style Names for a given anchor."""
    return [k for k, v in REACTION_STYLE_DB.items() if v.anchor == anchor]
