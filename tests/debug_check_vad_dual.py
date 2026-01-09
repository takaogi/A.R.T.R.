import sys
import time
from pathlib import Path
import shutil

# Add src import path
sys.path.append(str(Path(__file__).parent))

from src.systems.emotion.engine import VADEngine
from src.utils.logger import logger

def test_vad_dual_layer():
    logger.info("--- Starting Dual-Layer VAD Verification ---")
    
    char_name = "VADTestChar"
    # Cleanup previous test data
    import shutil
    data_dir = Path(f"data/characters/{char_name}")
    if data_dir.exists():
        try:
            shutil.rmtree(data_dir)
        except:
            pass
            
    # 1. Initialize
    config = {
        "vad_baseline": {"valence": 0.0, "arousal": 0.0, "dominance": 0.0},
        "vad_volatility": {"valence": 1.0, "arousal": 1.0, "dominance": 1.0}
    }
    
    engine = VADEngine(char_name, config)
    logger.info(f"Initialized: Surface({engine.surf_v:.2f}) Deep({engine.deep_v:.2f})")
    
    # 2. Test Updates (1/4 Impact Rule)
    # Update with +0.4 Valence
    engine.update(0.4, 0.0, 0.0)
    
    logger.info(f"After Update(+0.4): Surface V={engine.surf_v:.2f}, Deep V={engine.deep_v:.2f}")
    
    # Check Surface (Should be +0.4)
    if abs(engine.surf_v - 0.4) < 0.01:
        logger.success("Surface VAD updated correctly (100% impact).")
    else:
        logger.error(f"Surface VAD mismatch. Expected 0.4, got {engine.surf_v}")
        
    # Check Deep (Should be +0.1 because 0.4 * 0.25 = 0.1)
    if abs(engine.deep_v - 0.1) < 0.01:
        logger.success("Deep VAD updated correctly (25% impact).")
    else:
        logger.error(f"Deep VAD mismatch. Expected 0.1, got {engine.deep_v}")

    # 3. Test Persistence
    engine.save_state()
    del engine
    
    engine2 = VADEngine(char_name, config)
    logger.info(f"Reloaded: Surface V={engine2.surf_v:.2f}, Deep V={engine2.deep_v:.2f}")
    
    if abs(engine2.surf_v - 0.4) < 0.01 and abs(engine2.deep_v - 0.1) < 0.01:
        logger.success("Persistence (Save/Load) successful.")
    else:
        logger.error("Persistence failed.")

    # 4. Test Decay (Stub simulation)
    # Simulate decay logic directly or via method if time passed
    # Surface (0.4) should move towards Deep (0.1)
    # Deep (0.1) should move towards Baseline (0.0)
    
    logger.info("--- Testing Decay (Simulated 60s) ---")
    # Force a decay step
    engine2.decay(60.0) 
    
    logger.info(f"After Decay: Surface V={engine2.surf_v:.2f}, Deep V={engine2.deep_v:.2f}")
    
    # Surface should descend towards Deep (0.1)
    # Initial S=0.4, Target D=0.1. Decay rate approx 0.05 * 60 = 3.0 (capped at 1.0).
    # Wait, my decay logic was `surf_decay_rate = 0.05 * elapsed_seconds`.
    # 0.05 * 60 = 3.0. Since min(1.0, 3.0) is 1.0, it should fully converge to Deep in 60s?
    # Let's check logic implementation.
    
    if engine2.surf_v < 0.39: # Should definitely be lower than 0.4
         logger.success(f"Surface Decay occurred: {engine2.surf_v:.2f}")
    else:
         logger.error("Surface failed to decay.")
         
    if engine2.deep_v < 0.1: # Should move towards 0.0
         logger.success(f"Deep Decay occurred: {engine2.deep_v:.2f}")
    else:
         logger.error("Deep failed to decay.")

if __name__ == "__main__":
    test_vad_dual_layer()
