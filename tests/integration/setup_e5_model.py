import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.foundation.paths.manager import PathManager
from huggingface_hub import snapshot_download

def setup_e5():
    # Use standard PathManager
    # NOTE: model_id in code matches E5OnnxEmbeddingService default
    MODEL_ID = "Xenova/multilingual-e5-small"
    
    pm = PathManager.get_instance()
    models_dir = pm.get_models_dir()
    embed_dir = models_dir / "embedding"
    embed_dir.mkdir(exist_ok=True, parents=True)
    
    target_dir = embed_dir / MODEL_ID.replace("/", "_")
    
    print(f"Downloading {MODEL_ID} to {target_dir}...")
    
    # Download specific ONNX files
    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=str(target_dir),
        allow_patterns=["*.onnx", "tokenizer.json", "config.json", "special_tokens_map.json", "tokenizer_config.json"]
    )
    
    print("Download Complete.")

if __name__ == "__main__":
    setup_e5()
