import os
import sys
from pathlib import Path

def find_null_bytes(root_dir):
    print(f"Scanning {root_dir} RECURSIVELY for null bytes in .py files...")
    root = Path(root_dir)
    found_any = False
    
    for path in root.rglob("*.py"):
        try:
            with open(path, "rb") as f:
                content = f.read()
                if b'\x00' in content:
                    print(f"[FAIL] Null byte found in: {path}")
                    # Find position
                    pos = content.find(b'\x00')
                    print(f"       At byte offset: {pos}")
                    # Show surrounding bytes
                    start = max(0, pos - 10)
                    end = min(len(content), pos + 10)
                    print(f"       Context: {content[start:end]}")
                    found_any = True
                else:
                    # Pass
                    pass
        except Exception as e:
            print(f"[ERROR] Could not read {path}: {e}")

    if not found_any:
        print("[SUCCESS] No null bytes found in any .py file.")
    else:
        print("[FAILURE] Null bytes detected.")
        sys.exit(1)

if __name__ == "__main__":
    find_null_bytes(r"x:\Dev\C.R.A.D.L.E\A.R.T.R\src")
