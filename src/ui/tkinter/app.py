
import asyncio
import tkinter as tk
from tkinter import ttk
import logging
from typing import Optional, Dict

from src.core.controller import CoreController
from src.ui.tkinter.core.view_manager import ViewManager
from src.ui.tkinter.components.status_bar import StatusBar

class App(tk.Tk):
    """
    Main A.R.T.R. UI Application.
    Orchestrates CoreController and View Navigation.
    """
    def __init__(self, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.loop = loop
        self.title("A.R.T.R.")
        self.geometry("1024x768")
        
        # Initialize Core Controller (Non-blocking init scheduled)
        self.controller = CoreController()
        
        # Initialize Services
        from src.ui.tkinter.services.ui_config_service import UIConfigService
        self.ui_config_service = UIConfigService()
        
        # Setup Styles
        self._setup_styles()
        
        # UI Layout
        # Root Grid: 
        # Row 0: Header (Settings) - NEW
        # Row 1: Content (Expandable)
        # Row 2: Status Bar (Fixed)
        self.grid_rowconfigure(0, weight=0) # Header
        self.grid_rowconfigure(1, weight=1) # Content
        self.grid_rowconfigure(2, weight=0) # Status
        self.grid_columnconfigure(0, weight=1)

        # Header Frame
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        
        # Settings Button
        btn_settings = ttk.Button(header_frame, text="⚙ Settings", command=self._open_settings)
        btn_settings.pack(side=tk.LEFT)
        
        # Status Bar
        self.status_bar = StatusBar(self, self.controller)
        self.status_bar.grid(row=2, column=0, sticky="ew")
        
        # ViewManager
        self.view_manager = ViewManager(self, self.controller, self.ui_config_service)
        self.view_manager.grid(row=1, column=0, sticky="nsew")
        
        # Start System Init
        self.loop.create_task(self._bootstrap_system())
        
        # Start UI Update Loop
        self._on_update()

    def _open_settings(self):
        from src.ui.tkinter.views.ui_config_window import UIConfigWindow
        UIConfigWindow(self, self.ui_config_service)

    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            # Try to use a modern theme if available
            # style.theme_use('clam') 
            pass
        except:
            pass
            
    async def _bootstrap_system(self):
        """Initializes the backend controller."""
        self.status_bar.set_status("Initializing System...", "busy")
        try:
            await self.controller.initialize_system()
            self.status_bar.set_status("System Ready", "idle")
            
            # Navigate to Dashboard
            self.view_manager.show_view("dashboard")
            
        except Exception as e:
            self.status_bar.set_status(f"Error: {e}", "error")
            logging.error(f"Bootstrap failed: {e}")

    def _on_update(self):
        """
        Tkinter Main Loop integrated with Asyncio.
        Instead of root.mainloop(), we let the asyncio loop drive update(),
        or vice versa. Here we use basic polling.
        """
        self.update()
        
        # Poll any high frequency UI updates here if needed (e.g. download progress)
        self.status_bar.update_status()

        # Schedule next update
        # 1/60s ~= 16ms
        self.loop.call_later(0.016, self._on_update)
