import sys
import os
import asyncio
import time

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.controller import CoreController

async def main():
    print("=== A.R.T.R. Local LLM Real Verification ===")
    
    # 1. Init Controller
    controller = CoreController()
    await controller.initialize_system()
    
    # 2. Select 12GB Model
    target_preset_name = "12GB GPU (Mag-Mell 12B)"
    presets = controller.get_local_model_presets()
    target = next((p for p in presets if p.name == target_preset_name), None)
    
    if not target:
        print(f"[ERROR] Preset '{target_preset_name}' not found.")
        return

    print(f"\n[Selected Model] {target.name}")
    print(f"Repo: {target.repo_id}")
    print(f"File: {target.filename}")
    
    # 3. Start Download
    print("\n[Action] Starting Download...")
    success = controller.download_model(target.repo_id, target.filename)
    if not success:
        # Check if already done or error
        status = controller.get_download_status()
        if status.get("status") == "done":
             print("Model already downloaded.")
        else:
             print(f"Download start failed: {status}")
             return

    # 4. Monitor Download
    last_pct = -1
    while True:
        status = controller.get_download_status()
        st = status.get("status")
        pct = status.get("percent", 0)
        current_mb = status.get("current", 0) / (1024*1024)
        total_mb = status.get("total", 0) / (1024*1024)
        
        if pct != last_pct:
            print(f"[Download] {st.upper()}: {pct}% ({current_mb:.2f}MB / {total_mb:.2f}MB)")
            last_pct = pct
            
        if st == "done":
            print("\nDownload Complete!")
            break
        elif st == "error":
            print(f"\n[ERROR] Download Failed: {status.get('error')}")
            return
            
        time.sleep(2) # Update every 2 seconds

    # 5. Launch Server
    print("\n[Action] Launching Server...")
    launched = controller.start_local_llm(target.filename)
    
    if launched:
        print("Server launch command issued.")
        # Wait for potential startup
        time.sleep(10)
        
        if controller.local_model_manager.is_running():
             print("[SUCCESS] Server Process is RUNNING.")
             print(f"PID: {controller.local_model_manager.process.pid}")
        else:
             print("[ERROR] Server Process died immediately.")
    else:
        print("[ERROR] Failed to launch server.")

    # 6. Cleanup
    print("\n[Action] Stopping Server...")
    controller.stop_local_llm()
    print("Server Stopped.")

if __name__ == "__main__":
    asyncio.run(main())
