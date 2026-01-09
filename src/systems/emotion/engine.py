import json
import time
from pathlib import Path
from src.utils.logger import logger
from src.utils.path_helper import get_data_dir

class VADEngine:
    """
    Manages the Core Emotional State (VAD) using a Dual-Layer 'Moon & Earth' Gravity Model.
    
    Layers:
    1. Surface VAD (Moon, Mass 1): Instantaneous emotion. Decays quickly to Deep VAD.
    2. Deep VAD (Earth, Mass 4): Core mood baseline. Shifts solely by Affection/Base Personality.
    
    Updates:
    - User input affects Surface 100%, Deep 25%.
    - Deep acts as a gravity attractor for Surface.
    - Deep slowly decays to Baseline (or holds via Affection).
    """
    
    def __init__(self, char_name: str, config: dict = None):
        """
        Args:
            char_name: Character name for persistence.
            config: Optional dict containing 'vad_baseline' and 'vad_volatility'.
        """
        self.char_name = char_name
        self.config = config or {}
        
        # Paths
        self.data_dir = get_data_dir() / "characters" / char_name
        self.file_path = self.data_dir / "vad_state.json"

        # 1. Config Loading (Baseline & Volatility)
        baseline = self.config.get("vad_baseline", {})
        self.base_v = baseline.get("valence", 0.0)
        self.base_a = baseline.get("arousal", 0.0)
        self.base_d = baseline.get("dominance", 0.0)
        
        vol = self.config.get("vad_volatility", {})
        self.vol_v = vol.get("valence", 1.0)
        self.vol_a = vol.get("arousal", 1.0)
        self.vol_d = vol.get("dominance", 1.0)
        
        # 2. State Initialization
        # Deep VAD (Earth)
        self.deep_v = self.base_v
        self.deep_a = self.base_a
        self.deep_d = self.base_d
        
        # Surface VAD (Moon)
        self.surf_v = self.base_v
        self.surf_a = self.base_a
        self.surf_d = self.base_d
        
        self.last_update_time = time.time()
        
        # 3. Load Persistence
        self.load_state()
        
        logger.info(f"VAD Engine Initialized for '{char_name}'.")

    def load_state(self):
        """Load persistent VAD state if exists."""
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Deep
                    deep = data.get("deep", {})
                    self.deep_v = deep.get("v", self.base_v)
                    self.deep_a = deep.get("a", self.base_a)
                    self.deep_d = deep.get("d", self.base_d)
                    
                    # Surface
                    surf = data.get("surface", {})
                    self.surf_v = surf.get("v", self.deep_v)
                    self.surf_a = surf.get("a", self.deep_a)
                    self.surf_d = surf.get("d", self.deep_d)
                    
                    self.last_update_time = data.get("timestamp", time.time())
                
                # Perform decay for the time elapsed while offline?
                # Ideally yes, but let's just sync time for now to avoid jump cuts.
                self.decay(time.time() - self.last_update_time)
                
            except Exception as e:
                logger.error(f"Failed to load VAD state: {e}")

    def save_state(self):
        """Save persistent VAD state."""
        data = {
            "timestamp": time.time(),
            "deep": {"v": self.deep_v, "a": self.deep_a, "d": self.deep_d},
            "surface": {"v": self.surf_v, "a": self.surf_a, "d": self.surf_d}
        }
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save VAD state: {e}")

    def update(self, v_delta: float, a_delta: float, d_delta: float):
        """
        Updates VAD values.
        Surface receives full impact (scaled by volatility).
        Deep receives 1/4 impact.
        """
        # Calculate Volatility-Scaled Delta
        dv = v_delta * self.vol_v
        da = a_delta * self.vol_a
        dd = d_delta * self.vol_d
        
        # Update Surface (Clamp -1.0 to 1.0)
        self.surf_v = max(-1.0, min(1.0, self.surf_v + dv))
        self.surf_a = max(-1.0, min(1.0, self.surf_a + da))
        self.surf_d = max(-1.0, min(1.0, self.surf_d + dd))
        
        # Update Deep (1/4 Impact)
        deep_ratio = 0.25
        self.deep_v = max(-1.0, min(1.0, self.deep_v + (dv * deep_ratio)))
        self.deep_a = max(-1.0, min(1.0, self.deep_a + (da * deep_ratio)))
        self.deep_d = max(-1.0, min(1.0, self.deep_d + (dd * deep_ratio)))
        
        self.last_update_time = time.time()
        self.save_state()
        
        logger.info(f"VAD Update: Surface(+{dv:.2f}/+{da:.2f}/+{dd:.2f}), Deep(+{dv*deep_ratio:.2f}...)")

    def decay(self, elapsed_seconds: float):
        """
        Apply gravitational decay using Exponential Decay.
        Formula: Nt = N0 * exp(-lambda * t)
        Adapted: current = target + (start - target) * exp(-rate * dt)
        
        1. Surface is pulled towards Deep (Fast Decay).
        2. Deep is pulled towards Baseline (Slow Decay).
        """
        if elapsed_seconds <= 0: return

        import math

        # Decay Constants (Rate constant k)
        # Higher k = faster decay.
        # Surface -> Deep: Fast (e.g., half-life of 5 mins? -> k approx 0.002)
        # Let's say we want 50% decay in 300s. exp(-k*300) = 0.5 -> -k*300 = -0.693 -> k = 0.0023
        surf_k = 0.005 # Configurable?
        
        # Deep -> Baseline: Slow (e.g., half-life of 1 hour? -> k approx 0.0002)
        deep_k = 0.0005 

        # Surface -> Deep
        factor_surf = math.exp(-surf_k * elapsed_seconds)
        self.surf_v = self.deep_v + (self.surf_v - self.deep_v) * factor_surf
        self.surf_a = self.deep_a + (self.surf_a - self.deep_a) * factor_surf
        self.surf_d = self.deep_d + (self.surf_d - self.deep_d) * factor_surf
        
        # Deep -> Baseline
        factor_deep = math.exp(-deep_k * elapsed_seconds)
        self.deep_v = self.base_v + (self.deep_v - self.base_v) * factor_deep
        self.deep_a = self.base_a + (self.deep_a - self.base_a) * factor_deep
        self.deep_d = self.base_d + (self.deep_d - self.base_d) * factor_deep
        
        self.last_update_time = time.time()
        self.save_state()

    def get_state(self):
        """Return flattened state for context injection. Rounded for LLM readability."""
        return {
            "valence": round(self.surf_v, 2),
            "arousal": round(self.surf_a, 2),
            "dominance": round(self.surf_d, 2),
            "deep_valence": round(self.deep_v, 2), 
            "deep_arousal": round(self.deep_a, 2),
            "deep_dominance": round(self.deep_d, 2)
        }
