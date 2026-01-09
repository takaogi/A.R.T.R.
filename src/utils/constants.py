from pathlib import Path

# --- System Defaults ---
APP_NAME = "A.R.T.R."
VERSION = "0.1.0"

# --- VAD (Valence, Arousal, Dominance) Defaults ---
# Range: -1.0 to 1.0 (internal normalization usually maps to this or -0.2 to 0.2 for deltas)
DEFAULT_VAD_BASELINE = {"valence": 0.0, "arousal": 0.0, "dominance": 0.0}
VAD_MIN = -1.0
VAD_MAX = 1.0

# --- Pacemaker Defaults ---
# Base intervals in seconds
PACEMAKER_BASE_INTERVAL_OBSESSIVE = 20
PACEMAKER_BASE_INTERVAL_NORMAL = 180  # 3 minutes
PACEMAKER_BASE_INTERVAL_LAZY = 900    # 15 minutes

# --- Memory Defaults ---
MAX_SHORT_TERM_MEMORY = 20  # Number of turns to keep in context before archival/summarization considerations
DEFAULT_OBSESSION_TTL = 1   # Default turns for an Inner Voice goal to live

# --- File Extensions ---
CHARACTER_CARD_EXTENSIONS = [".json", ".png"] # PNG for V2 Spec embedded cards (future)
LOG_EXTENSION = ".log"

# --- UI Constants ---
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
CHAT_FONT_FAMILY = "Meiryo UI" # Good for Japanese text
CHAT_FONT_SIZE = 12

# --- Vision System ---
WHITE_ROOM_DIR_NAME = "white_room"
VISION_CACHE_FILE = "vision_cache.json"
