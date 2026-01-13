import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from src.foundation.paths import PathManager

def verify_paths():
    print("--- Starting Path Verification ---")
    
    manager = PathManager.get_instance()
    
    print(f"Frozen State (sys.frozen): {getattr(sys, 'frozen', False)}")
    
    root = manager.root_dir
    print(f"Root Dir: {root}")
    
    log_dir = manager.get_log_dir()
    print(f"Log Dir: {log_dir} (Exists: {log_dir.exists()})")
    
    data_dir = manager.get_data_dir()
    print(f"Data Dir: {data_dir} (Exists: {data_dir.exists()})")
    
    config_path = manager.get_config_path()
    print(f"Config Path: {config_path} (Exists: {config_path.exists()})")

    # Sanity check
    if not (root / "config.yaml").exists():
        print("[WARN] config.yaml not found at detected root!")
    else:
        print("[OK] config.yaml found at root.")

if __name__ == "__main__":
    verify_paths()
