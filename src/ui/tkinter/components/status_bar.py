
import tkinter as tk
from tkinter import ttk

class StatusBar(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, relief=tk.SUNKEN, padding=(5, 2))
        self.controller = controller
        
        # Layout
        self.columnconfigure(1, weight=1) # Spacer
        
        # 1. System Status Label
        self.status_label = ttk.Label(self, text="Initializing...", width=30)
        self.status_label.grid(row=0, column=0, sticky="w")
        
        # 2. Download Progress (Initially Hidden)
        self.progress_frame = ttk.Frame(self)
        self.progress_label = ttk.Label(self.progress_frame, text="Download: 0%")
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient="horizontal", length=200, mode="determinate")
        
        self.progress_label.pack(side=tk.LEFT, padx=5)
        self.progress_bar.pack(side=tk.LEFT, padx=5)
        
        # 3. Resource Monitor (Right)
        # TODO: Implement VRAM polling
        self.res_label = ttk.Label(self, text="RAM: --- | VRAM: ---")
        self.res_label.grid(row=0, column=2, sticky="e", padx=10)
        
        self._download_visible = False

    def set_status(self, text: str, state: str = "idle"):
        self.status_label.config(text=text)
        # Could change color based on state (idle=black, thinking=blue, error=red)
        if state == "error":
            self.status_label.config(foreground="red")
        elif state == "busy":
            self.status_label.config(foreground="blue")
        else:
            self.status_label.config(foreground="black")

    def update_status(self):
        """Called periodically by main loop."""
        # 1. Check Download Status
        dl_status = self.controller.get_download_status()
        if dl_status.get("status") == "downloading":
            self._show_download(True)
            pct = dl_status.get("percent", 0)
            cur = dl_status.get("current", 0) / (1024*1024)
            tot = dl_status.get("total", 0) / (1024*1024)
            
            self.progress_bar["value"] = pct
            self.progress_label.config(text=f"DL: {pct}% ({cur:.1f}/{tot:.1f} MB)")
        else:
            self._show_download(False)

    def _show_download(self, show: bool):
        if show and not self._download_visible:
            self.progress_frame.grid(row=0, column=1, sticky="e", padx=20)
            self._download_visible = True
        elif not show and self._download_visible:
            self.progress_frame.grid_forget()
            self._download_visible = False
