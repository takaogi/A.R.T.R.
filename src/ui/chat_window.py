import tkinter as tk
from tkinter import ttk, scrolledtext
import asyncio
import threading
from src.config import settings
from src.ui.character_selector import show_selection_dialog
from src.systems.core.system_core import SystemCore
from src.layers.reflex import reflex_layer

class ChatWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.withdraw() # Hide until selection
        
        # Character Selection
        char_name = show_selection_dialog(self.root)
        if not char_name:
            self.root.destroy()
            return

        self.char_name = char_name
        self.root.deiconify() # Show window IMMEDIATELY
        
        self.root.title(f"{settings.APP_NAME} v{settings.VERSION} - {self.char_name}")
        self.root.geometry("800x600")

        # Grid Layout
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1) # Chat Log
        self.root.rowconfigure(1, weight=0) # Input Area
        
        # 1. Chat Log Area
        self.chat_log = scrolledtext.ScrolledText(self.root, state='disabled', font=("Meiryo UI", 12))
        self.chat_log.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.chat_log.tag_config("user", foreground="blue")
        self.chat_log.tag_config("bot", foreground="black")
        self.chat_log.tag_config("system", foreground="gray")
        self.chat_log.tag_config("loading", foreground="orange")
        
        # 2. Input Frame
        input_frame = ttk.Frame(self.root)
        input_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        input_frame.columnconfigure(0, weight=1)
        
        self.entry = ttk.Entry(input_frame, font=("Meiryo UI", 12))
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.entry.bind("<Return>", self.on_send)
        self.entry.configure(state='disabled') # Disable until loaded
        
        self.send_btn = ttk.Button(input_frame, text="Loading...", command=self.on_send)
        self.send_btn.grid(row=0, column=1)
        self.send_btn.configure(state='disabled')
        
        self.append_log("System", f"Starting initialization for '{self.char_name}'...", "system")
        
        # Start Loading in Background Thread
        threading.Thread(target=self.initialize_system_background, daemon=True).start()

    def update_loading_status(self, message: str):
        """Callback for background thread to update UI log."""
        self.root.after(0, self.append_log, "Loader", message, "loading")

    def initialize_system_background(self):
        try:
            # Initialize Core Layers for this Character
            # Pass our callback to SystemCore -> PersonalityManager
            self.system_core = SystemCore(self.char_name, progress_callback=self.update_loading_status)
            
            # Initialize Reflex Layer (Also could take callback if updated, but maybe fast enough?)
            self.update_loading_status("Initializing Reflex Layer...")
            reflex_layer.load_character(self.char_name) # Assuming this is fast or we update it too
            
            # Done
            self.root.after(0, self.on_loading_complete)
            
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, self.on_loading_error, err_msg)

    def on_loading_complete(self):
        self.append_log("System", "Initialization Complete. Ready.", "system")
        self.entry.configure(state='normal')
        self.send_btn.configure(state='normal', text="Send")
        self.entry.focus()

    def on_loading_error(self, error_msg):
        self.append_log("System", f"FATAL ERROR: {error_msg}", "system")
        # Keep disabled or show exit button?
        
    # --- Renaming on_send to avoid confusion if needed, but keeping existing valid ---


    def append_log(self, sender: str, message: str, tag: str = "system"):
        self.chat_log.configure(state='normal')
        self.chat_log.insert(tk.END, f"[{sender}]: {message}\n", tag)
        self.chat_log.configure(state='disabled')
        self.chat_log.see(tk.END)

    def on_send(self, event=None):
        text = self.entry.get().strip()
        if not text:
            return
        
        self.append_log("User", text, "user")
        self.entry.delete(0, tk.END)
        
        # Run async processing in a separate thread
        threading.Thread(target=self.run_async_reflex, args=(text,), daemon=True).start()

    def run_async_reflex(self, text):
        # Create a new event loop for this thread or use a global one
        # For simplicity in this threaded model, new loop per request (or run_until_complete)
        try:
            # Call SystemCore (Handles Attention/Routing/Translation)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response_list = loop.run_until_complete(self.system_core.process_input(text))
            
            # Use the last response for UI (or join them?)
            # Usually response_list is [str, str...].
            final_response = "\n".join(response_list)
            loop.close()
            
            # Update UI in main thread
            self.root.after(0, self.append_log, "A.R.T.R", final_response, "bot")
            
        except Exception as e:
            self.root.after(0, self.append_log, "System", f"Error: {e}", "system")
