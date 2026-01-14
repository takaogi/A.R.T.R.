import os
import sys
import subprocess
import requests
import threading
from typing import List, Optional, Dict, Callable, Any
from pathlib import Path
from src.foundation.config import ConfigManager
from src.foundation.logging import logger
from src.foundation.config.schema import LocalModelPreset

class LocalModelManager:
    """
    Manages Local LLM Server (llama-cpp-python) and Model Downloads.
    """
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.process: Optional[subprocess.Popen] = None
        self.download_status: Dict[str, Any] = {
            "status": "idle",
            "filename": "",
            "percent": 0,
            "current": 0,
            "total": 0,
            "error": None
        }
        self._download_thread: Optional[threading.Thread] = None

    @property
    def config(self):
        return self.config_manager.config.local_llm

    def get_model_dir(self) -> Path:
        """Resolves model directory."""
        path = Path(self.config.model_dir)
        if not path.is_absolute():
            # Assume relative to project root
            # ConfigManager doesn't expose root path directly easily, but we can assume cwd or relative to execution.
            # Ideally ConfigManager should handle path resolution, but for now we assume CWD.
            path = Path.cwd() / path
        return path

    def scan_models(self) -> List[str]:
        """Returns list of .gguf filenames in model_dir."""
        model_dir = self.get_model_dir()
        if not model_dir.exists():
            return []
        return [f.name for f in model_dir.glob("*.gguf")]

    def get_presets(self) -> List[LocalModelPreset]:
        return self.config.presets

    def get_download_status(self) -> Dict[str, Any]:
        """Returns current download status."""
        return self.download_status.copy()

    def download_model(self, repo_id: str, filename: str, progress_callback: Callable[[int, int], None] = None):
        """
        Starts a background thread to download the model.
        Updates self.download_status.
        """
        if self.download_status["status"] == "downloading":
             logger.warning("Download already in progress.")
             return False

        def _download_task():
            try:
                self.download_status = {
                    "status": "downloading",
                    "filename": filename,
                    "repo_id": repo_id,
                    "percent": 0,
                    "current": 0,
                    "total": 0,
                    "error": None
                }
                
                model_dir = self.get_model_dir()
                model_dir.mkdir(parents=True, exist_ok=True)
                target_path = model_dir / filename
                
                # Construct HF URL
                # https://huggingface.co/{repo_id}/resolve/main/{filename}
                url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
                logger.info(f"Starting download: {url} -> {target_path}")

                response = requests.get(url, stream=True)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                block_size = 8192 # 8KB
                current_size = 0
                
                with open(target_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=block_size):
                        if chunk:
                            f.write(chunk)
                            current_size += len(chunk)
                            
                            # Update Status
                            pct = int((current_size / total_size) * 100) if total_size > 0 else 0
                            self.download_status["current"] = current_size
                            self.download_status["total"] = total_size
                            self.download_status["percent"] = pct
                            
                            if progress_callback:
                                try:
                                    progress_callback(current_size, total_size)
                                except:
                                    pass

                logger.info("Download completed successfully.")
                self.download_status["status"] = "done"
                self.download_status["percent"] = 100
                
            except Exception as e:
                logger.error(f"Download failed: {e}")
                self.download_status["status"] = "error"
                self.download_status["error"] = str(e)

        self._download_thread = threading.Thread(target=_download_task, daemon=True)
        self._download_thread.start()
        return True

    def launch_server(self, model_filename: str) -> bool:
        """
        Launches llama_cpp.server subprocess.
        """
        if self.is_running():
            self.stop_server()
            
        model_path = self.get_model_dir() / model_filename
        if not model_path.exists():
            logger.error(f"Model not found: {model_path}")
            logger.error("Please download the model via the UI (Settings -> Local LLM) or place the .gguf file in the 'data/models/llm' directory.")
            return False
            
        # Command Construction
        # python -m llama_cpp.server --model ...
        
        cmd = [
            sys.executable,
            "-m", "llama_cpp.server",
            "--model", str(model_path),
            "--n_ctx", str(self.config.context_size),
            "--n_gpu_layers", str(self.config.gpu_layers),
            "--port", "8000"
        ]
        
        try:
            logger.info(f"Launching Local Server: {' '.join(cmd)}")
            self.process = subprocess.Popen(
                cmd,
                # stdout=subprocess.PIPE, 
                # stderr=subprocess.PIPE
            )
            
            # Check for immediate failure (e.g. corrupted model)
            try:
                # Wait 1s to see if it crashes immediately
                self.process.wait(timeout=1.0)
                # If we get here, it exited (crashed)
                ret = self.process.returncode
                logger.error(f"Server exited immediately with code {ret}. Check console for details.")
                self.process = None
                return False
            except subprocess.TimeoutExpired:
                # Still running after 1s -> Good
                return True
                
        except Exception as e:
            logger.error(f"Failed to launch server: {e}")
            return False

    def stop_server(self):
        if self.process:
            logger.info("Stopping Local Server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None

    def is_running(self) -> bool:
        if self.process:
            if self.process.poll() is None:
                return True
            self.process = None
        return False
