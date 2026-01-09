from pydantic import BaseModel, Field

class PacemakerConfig(BaseModel):
    base_interval_sec: int = Field(..., description="Base interval in seconds for autonomous thoughts (e.g. 300 for quiet, 60 for energetic).")
    variance: float = Field(..., description="Variance (0.0-1.0) of the interval. Actual interval = Base +/- (Base * Variance * Random).")

class VadBaseline(BaseModel):
    valence: float = Field(..., description="Baseline Valence (-1.0 to 1.0). Negative=Depressed/Dark, Positive=Happy/Bright.")
    arousal: float = Field(..., description="Baseline Arousal (-1.0 to 1.0). Negative=Calm/Sleepy, Positive=Excited/Active.")
    dominance: float = Field(..., description="Baseline Dominance (-1.0 to 1.0). Negative=Submissive/Weak, Positive=Dominant/Strong.")

class VadVolatility(BaseModel):
    valence: float = Field(..., description="Volatility of Valence (0.1 to 3.0). Higher = More mood swings.")
    arousal: float = Field(..., description="Volatility of Arousal (0.1 to 3.0). Higher = Easily excited/calmed.")
    dominance: float = Field(..., description="Volatility of Dominance (0.1 to 3.0). Higher = Confidence fluctuates easily.")

class SystemParameterSchema(BaseModel):
    pacemaker: PacemakerConfig
    vad_baseline: VadBaseline
    vad_volatility: VadVolatility
