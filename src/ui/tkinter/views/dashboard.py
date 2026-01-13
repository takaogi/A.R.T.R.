
import tkinter as tk
from tkinter import ttk
import logging

class DashboardView(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        # self.parent = parent (ViewManager)
        
        # Header
        self.header = ttk.Label(self, text="A.R.T.R. Dashboard", font=("Segoe UI", 16, "bold"))
        self.header.pack(pady=20)
        
        # Content Area
        self.content = ttk.Frame(self)
        self.content.pack(fill=tk.BOTH, expand=True, padx=50)
        
        # --- Local LLM Section ---
        self._build_llm_section()
        
        # --- Actions Section ---
        self._build_actions_section()

    def _build_llm_section(self):
        frame = ttk.Labelframe(self.content, text="Local LLM Settings", padding=10)
        frame.pack(fill=tk.X, pady=10)
        
        # Preset Selection
        ttk.Label(frame, text="Model Preset:").grid(row=0, column=0, sticky="w")
        
        self.presets = self.controller.get_local_model_presets()
        self.preset_var = tk.StringVar()
        
        # Extract names properly
        preset_names = [p.name for p in self.presets]
        if preset_names:
            self.preset_var.set(preset_names[0])
            
        self.combo_presets = ttk.Combobox(frame, textvariable=self.preset_var, values=preset_names, state="readonly", width=40)
        self.combo_presets.grid(row=0, column=1, sticky="w", padx=10)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky="w")
        
        self.btn_download = ttk.Button(btn_frame, text="Download", command=self._on_download)
        self.btn_download.pack(side=tk.LEFT, padx=5)
        
        self.btn_launch = ttk.Button(btn_frame, text="Launch Service", command=self._on_launch)
        self.btn_launch.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = ttk.Button(btn_frame, text="Stop Service", command=self._on_stop)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

    def _build_actions_section(self):
        frame = ttk.Labelframe(self.content, text="System Actions", padding=10)
        frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(frame, text="Select Character >>", command=self._on_select_char).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="Exit", command=self.quit).pack(side=tk.RIGHT, padx=5)

    # --- Events ---
    
    def _get_current_preset(self):
        name = self.preset_var.get()
        return next((p for p in self.presets if p.name == name), None)

    def _on_download(self):
        preset = self._get_current_preset()
        if preset:
            logging.info(f"[UI] Requesting download: {preset.name}")
            self.controller.download_model(preset.repo_id, preset.filename)
            # Progress bar updates via StatusBar polling

    def _on_launch(self):
        preset = self._get_current_preset()
        if preset:
            logging.info(f"[UI] Launching server: {preset.filename}")
            self.controller.start_local_llm(preset.filename)

    def _on_stop(self):
        logging.info(f"[UI] Stopping server.")
        self.controller.stop_local_llm()

    def _on_select_char(self):
        # Navigate to Character Select (View 2)
        # parent is ViewManager
        self.master.show_view("character_select")
