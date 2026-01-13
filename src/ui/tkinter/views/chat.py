
import tkinter as tk
from tkinter import ttk, scrolledtext
import logging
from typing import TYPE_CHECKING
from src.ui.tkinter.components.tachie_display import TachieDisplay

if TYPE_CHECKING:
    from src.ui.tkinter.core.view_manager import ViewManager

class ChatView(ttk.Frame):
    def __init__(self, parent: 'ViewManager', controller):
        super().__init__(parent)
        self.controller = controller
        
        # Layout: Grid
        # Col 0: Chat Log (Weight 1)
        # Col 1: Tachie (Weight 1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        
        # --- Left Panel: Chat & Input ---
        left_panel = ttk.Frame(self)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Chat Log
        self.chat_log = scrolledtext.ScrolledText(left_panel, font=("Segoe UI Emoji", 11), state="disabled", wrap="word")
        self.chat_log.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Configure Tags
        self.chat_log.tag_config("user", foreground="#4a90e2", font=("Segoe UI", 11, "bold"))
        self.chat_log.tag_config("ai", foreground="#50e3c2", font=("Segoe UI", 11, "bold"))
        self.chat_log.tag_config("thought", foreground="gray", font=("Segoe UI", 10, "italic"))
        self.chat_log.tag_config("system", foreground="#f5a623", font=("Consolas", 9))
        
        # Auto-Scroll
        
        # Start/Stop Button (for debug/test)
        
        # Input Area
        input_frame = ttk.Frame(left_panel)
        input_frame.pack(fill=tk.X)
        
        self.entry = ttk.Entry(input_frame, font=("Segoe UI", 11))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", self._on_send)
        
        self.btn_send = ttk.Button(input_frame, text="Send", command=self._on_send)
        self.btn_send.pack(side=tk.RIGHT, padx=5)
        
        # --- Right Panel: Tachie ---
        self.tachie_panel = TachieDisplay(self)
        self.tachie_panel.grid(row=0, column=1, sticky="nsew")
        
        # State
        self.last_history_len = 0
        self.polling_task = None
        
        # Thinking Indicator
        self.thinking_label = ttk.Label(left_panel, text="Thinking...", foreground="blue")
        # Hidden by default

    def on_show(self):
        # Initialize Tachie
        # Initialize Tachie
        app = self.master.master
        
        if self.controller.current_profile:
            # Use the actual directory name from manager if available to ensure assets are found
            dir_name = None
            if self.controller.character_manager:
                dir_name = self.controller.character_manager.character_name
                
            self.tachie_panel.set_character(self.controller.current_profile, directory_name=dir_name)
            
            # Restore History
            try:
                history = self.controller.get_chat_history(limit=100)
                if history:
                    # Clear and populate
                    self.chat_log.config(state="normal")
                    self.chat_log.delete("1.0", tk.END)
                    self.chat_log.config(state="disabled")
                    self._update_log(history)
            except Exception as e:
                logging.error(f"Failed to restore history: {e}")
            
        # Start Polling Loop
        # Ensure only one loop
        # We can use 'after' loop in Tkinter natively instead of asyncio polling if simpler, 
        # but let's stick to existing pattern if it works.
        # But wait, self.polling_task isn't actually used to cancel.
        # We should use a flag or ensure we don't start double loops if on_show called multiple times (switching views).
        # We assume 'on_hide' might be needed or we just run loop always but skip if not visible?
        # For now, let's just start it if checks pass.
        
        if hasattr(app, 'loop'):
            # Only start if not running? 
            # Simple check: pass
            self._poll_history(app.loop)

    def _poll_history(self, loop):
        # Poll engine history
        if not self.winfo_exists():
            return
            
        if self.controller._is_initialized and self.controller.memory_manager:
            history = self.controller.memory_manager.get_context_history() # returns list of dict
            if len(history) > self.last_history_len:
                new_items = history[self.last_history_len:]
                self._update_log(new_items)
                self.last_history_len = len(history)
                
            # Update Tachie Expression
            if self.controller.character_manager:
                state = self.controller.character_manager.get_state()
                if state.current_expression:
                    self.tachie_panel.update_expression(state.current_expression)

            # Check Thinking State (Engine running?)
            # engine.running or check _current_task
            if self.controller.engine and self.controller.engine._current_task and not self.controller.engine._current_task.done():
                 self.thinking_label.pack(side=tk.BOTTOM, anchor="w")
            else:
                 self.thinking_label.pack_forget()

        # Reschedule
        loop.call_later(0.5, lambda: self._poll_history(loop))

    def _update_log(self, items):
        self.chat_log.config(state="normal")
        for item in items:
            role = item.get("role")
            content = item.get("content")
            
            if role == "user":
                self.chat_log.insert(tk.END, f"\nUser: {content}\n", "user")
            elif role == "assistant":
                # Check if thought or talk. 
                # If content starts with (Thought) or similar, we might want to hide it.
                # User request: Hide thoughts.
                # However, current MemoryManager usually stores thoughts cleanly separate or mixed?
                # MemoryManager.add_thought -> role='assistant', content='(Thought) ...'
                # Let's filter based on content heuristic or just skip if we know it's a thought step.
                
                # Heuristic: If content starts with "(Thought)", skip.
                if content.strip().startswith("(Thought)"):
                    continue
                    
                self.chat_log.insert(tk.END, f"\nAI: {content}\n", "ai")
                
                # Update Tachie if expression present in content? 
                # No, expression is in CognitiveResponse, not necessarily in history text.
                # History mainly stores 'talk'.
                # To get expression, we probably need deeper integration or check last response object.
                # For now, simplistic approach.
            elif role == "system":
                self.chat_log.insert(tk.END, f"[System]: {content}\n", "system")
                
        self.chat_log.see(tk.END)
        self.chat_log.config(state="disabled")

    def _on_send(self, event=None):
        text = self.entry.get().strip()
        if not text: return
        
        self.entry.delete(0, tk.END)
        self.thinking_label.pack(side=tk.BOTTOM, anchor="w")
        
        # Async Send
        app = self.master.master
        if hasattr(app, 'loop'):
            app.loop.create_task(self.controller.handle_user_input(text))
