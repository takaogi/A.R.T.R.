
import tkinter as tk
from tkinter import ttk, colorchooser
from typing import Dict
from src.ui.tkinter.services.ui_config_service import UIConfigService

class UIConfigWindow(tk.Toplevel):
    def __init__(self, parent, config_service: UIConfigService):
        super().__init__(parent)
        self.config_service = config_service
        self.title("UI Settings")
        self.geometry("400x300")
        
        self.current_config = self.config_service.get_config()
        
        self._setup_ui()

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Color Pickers
        self._create_color_row(main_frame, 0, "Background Color", "background_color")
        # replaced normal_text_color with slider
        self._create_speed_slider(main_frame, 1, "Typing Speed", "typing_speed")
        self._create_color_row(main_frame, 2, "User Text Color", "user_text_color")
        self._create_color_row(main_frame, 3, "AI Text Color", "ai_text_color")

        # Save Button
        save_btn = ttk.Button(main_frame, text="Save Settings", command=self._save)
        save_btn.grid(row=4, column=0, columnspan=3, pady=20)

    def _create_speed_slider(self, parent, row, label_text, config_key):
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", pady=5)
        
        # Slider Range: 0 (Slow: 0.1) -> 100 (Fast: 0.0)
        # Delay = (100 - val) / 100 * 0.1
        # Inverse: Val = 100 - (Delay / 0.1 * 100)
        
        current_delay = float(self.current_config.get(config_key, 0.02))
        initial_val = 100 - (current_delay / 0.1 * 100)
        initial_val = max(0, min(100, initial_val))
        
        lbl_val = ttk.Label(parent, text="")
        lbl_val.grid(row=row, column=2, padx=10)
        
        def on_change(val):
            v = float(val)
            # Calculate delay
            delay = (100 - v) / 100 * 0.1
            if delay < 0.005: delay = 0.0 # Snap to 0
            
            self.current_config[config_key] = delay
            
            if delay == 0:
                lbl_val.config(text="Instant")
            else:
                lbl_val.config(text=f"{delay:.3f}s")
                
            self.config_service.update_config(self.current_config)

        scale = ttk.Scale(parent, from_=0, to=100, orient=tk.HORIZONTAL, command=on_change)
        scale.set(initial_val)
        scale.grid(row=row, column=1, padx=10, sticky="ew")
        
        # Init Label
        on_change(initial_val)

    def _create_color_row(self, parent, row, label_text, config_key):
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", pady=5)
        
        # Color Preview/Button
        current_color = self.current_config.get(config_key, "#ffffff")
        
        # We use a Label as a preview and button trigger
        lbl_preview = tk.Label(parent, bg=current_color, width=10, relief="solid", borderwidth=1)
        lbl_preview.grid(row=row, column=1, padx=10, pady=5)
        
        btn_pick = ttk.Button(parent, text="Pick", command=lambda: self._pick_color(config_key, lbl_preview))
        btn_pick.grid(row=row, column=2, pady=5)

    def _pick_color(self, key, preview_label):
        initial_color = self.current_config.get(key, "#ffffff")
        color = colorchooser.askcolor(color=initial_color, title=f"Choose {key}")
        
        if color[1]: # color is ((r,g,b), hex)
            hex_color = color[1]
            self.current_config[key] = hex_color
            preview_label.config(bg=hex_color)
            
            # Immediate reflection
            self.config_service.update_config(self.current_config)

    def _save(self):
        self.config_service.save_config()
        self.destroy()
