import time
from src.config import settings
from src.utils.logger import logger

class AttentionManager:
    def __init__(self, 
                 decay_rate: float = settings.ATTENTION_DECAY_RATE, 
                 boost_amount: float = settings.ATTENTION_BOOST_DEFAULT, 
                 threshold: float = settings.ATTENTION_THRESHOLD):
        self.value = 0.0 # Start low to simulate waking up
        self.last_update = time.time()
        
        # Config 
        self.decay_rate = decay_rate
        self.boost_amount = boost_amount
        self.threshold = threshold
        
        # Clamp constants
        self.MIN_VAL = 0.0
        self.MAX_VAL = 1.0

    def update_decay(self):
        """
        Applies decay based on elapsed time since last update.
        """
        now = time.time()
        elapsed = now - self.last_update
        self.last_update = now
        
        # Linear decay for now
        # If decay level is 0.01 per second, and 10 seconds passed -> -0.1
        decay = self.decay_rate * elapsed
        if decay > 0:
            old_val = self.value
            self.value = max(self.MIN_VAL, self.value - decay)
            # logger.debug(f"Attention Decay: {old_val:.3f} -> {self.value:.3f} (Elapsed: {elapsed:.1f}s)")

    def boost(self, amount: float = None):
        """
        Increases attention value (e.g., on user input).
        """
        amt = amount if amount is not None else self.boost_amount
        old_val = self.value
        self.value = min(self.MAX_VAL, self.value + amt)
        self.update_decay() # Reset timer effectively by updating last_update to now
        logger.info(f"Attention Boost: {old_val:.3f} -> {self.value:.3f} (+{amt})")

    def is_attentive(self) -> bool:
        """
        Returns True if attention is above threshold.
        """
        self.update_decay() # Ensure current value is fresh
        return self.value >= self.threshold

    def get_value(self) -> float:
        self.update_decay()
        return self.value

    def reset_timer(self):
        self.last_update = time.time()
