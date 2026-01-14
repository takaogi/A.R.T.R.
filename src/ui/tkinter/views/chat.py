
import tkinter as tk
from tkinter import ttk, scrolledtext
import logging
import asyncio
from typing import TYPE_CHECKING
from src.ui.tkinter.components.tachie_display import TachieDisplay

if TYPE_CHECKING:
    from src.ui.tkinter.core.view_manager import ViewManager

class ChatView(ttk.Frame):
    def __init__(self, parent: 'ViewManager', controller, ui_config_service=None):
        super().__init__(parent)
        self.controller = controller
        self.ui_config_service = ui_config_service
        
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
        
        # Configure Tags (Initial)
        self._update_styles(self.ui_config_service.get_config() if self.ui_config_service else {})
        
        self.chat_log.tag_config("thought", foreground="gray", font=("Segoe UI", 10, "italic"))
        self.chat_log.tag_config("system", foreground="#f5a623", font=("Consolas", 9))
        
        # Subscribe to changes
        if self.ui_config_service:
            self.ui_config_service.subscribe(self._update_styles)
        
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
        self.last_timestamp = 0.0
        self.polling_task = None
        
        # Thinking Indicator
        self.thinking_label = ttk.Label(left_panel, text="Thinking...", foreground="blue")
        # Hidden by default

    def _update_styles(self, config: dict):
        # Apply Background
        bg_color = config.get("background_color", "#ffffff")
        norm_text = config.get("normal_text_color", "#000000")
        
        self.chat_log.config(bg=bg_color, fg=norm_text)
        
        # Apply Tag Colors
        user_color = config.get("user_text_color", "#4a90e2")
        ai_color = config.get("ai_text_color", "#50e3c2")
        
        self.chat_log.tag_config("user", foreground=user_color, font=("Segoe UI", 11, "bold"))
        self.chat_log.tag_config("ai", foreground=ai_color, font=("Segoe UI", 11, "bold"))

    def on_show(self):
        # Initialize Tachie
        app = self.master.master
        
        if self.controller.current_profile:
            self.tachie_panel.set_character(self.controller.current_profile)
            
            # Restore History
            try:
                history = self.controller.get_chat_history(limit=100)
                if history:
                    # Clear and populate
                    self.chat_log.config(state="normal")
                    self.chat_log.delete("1.0", tk.END)
                    self.chat_log.config(state="disabled")
                    
                    # For restore, just show instantly
                    self._update_log(history, instant=True)
                    
                    # Update last timestamp
                    if history:
                        self.last_timestamp = max(item.get("timestamp", 0) for item in history)
            except Exception as e:
                logging.error(f"Failed to restore history: {e}")
            
        # Start Polling Loop (Async)
        if hasattr(app, 'loop'):
            self.polling = True
            app.loop.create_task(self._poll_loop())

    async def _poll_loop(self):
        """Async polling loop ensuring UI updates don't freeze main thread."""
        try:
            while self.winfo_exists():
                try:
                    if self.controller._is_initialized and self.controller.memory_manager:
                        # 1. Update Thinking Status / Writing Indicator
                        # Engine task check
                        is_thinking = False
                        if self.controller.engine and self.controller.engine._current_task and not self.controller.engine._current_task.done():
                            is_thinking = True
                        
                        if is_thinking:
                            name = "AI"
                            if self.controller.current_profile:
                                name = self.controller.current_profile.name
                            self.thinking_label.config(text=f"{name} が書き込み中...")
                            self.thinking_label.pack(side=tk.BOTTOM, anchor="w", padx=10)
                        else:
                            self.thinking_label.pack_forget()

                        # 2. Check History
                        history = self.controller.memory_manager.get_context_history()
                        new_items = [item for item in history if item.get("timestamp", 0) > self.last_timestamp]

                        if new_items:
                            # Use Formatter logic to filter (Centralized logic)
                            from src.modules.memory.formatter import ConversationFormatter
                            formatter = ConversationFormatter()
                            visible_items = formatter.format_for_restore(new_items)
                            
                            if visible_items:
                                # Process new items (await typewriter if needed)
                                await self._update_log_async(visible_items)
                            
                            self.last_timestamp = max(self.last_timestamp, max(item.get("timestamp", 0) for item in new_items))

                        # 3. Update Tachie Expression
                        if self.controller.character_manager:
                            state = self.controller.character_manager.get_state()
                            if state.current_expression:
                                self.tachie_panel.update_expression(state.current_expression)

                except Exception as e:
                    logging.error(f"Poll Error: {e}")

                await asyncio.sleep(0.5)
                
        except tk.TclError:
            pass
        except Exception as e:
            logging.error(f"Poll Fatal Error: {e}")
                
        except tk.TclError:
            # Application destroyed
            pass
        except Exception as e:
            logging.error(f"Poll Fatal Error: {e}")

    def _update_log(self, items, instant=False):
        # Synchronous wrapper (legacy or restore) - treats all as instant
        for item in items:
            self._insert_item(item, instant=True)

    async def _update_log_async(self, items):
        # Async update allowing typewriter effect
        for item in items:
            role = item.get("role")
            # If AI, use config speed. Else instant.
            is_ai = (role == "assistant")
            
            # Determine Speed
            speed = 0.0
            if is_ai and self.ui_config_service:
                cfg = self.ui_config_service.get_config()
                speed = float(cfg.get("typing_speed", 0.02))
            
            # Insert
            await self._insert_item_async(item, speed)

    async def _insert_item_async(self, item, speed):
        role = item.get("role")
        content = item.get("content")
        
        # Redundant filters removed (Handled by format_for_restore upstream)

        tag = "system"
        header = "[System]"
        
        if role == "user":
            tag = "user"
            header = "User"
            speed = 0 # User always instant
        elif role == "assistant":
            tag = "ai"
            if self.controller.current_profile:
                header = self.controller.current_profile.name
            else:
                header = "AI"
        
        self.chat_log.config(state="normal")
        self.chat_log.insert(tk.END, f"\n{header}: ", tag)
        
        # Content
        if speed <= 0.001:
            # Instant
            self.chat_log.insert(tk.END, f"{content}\n", tag)
        else:
            # Typewriter
            await self._typewriter_effect(content, tag, speed)
            self.chat_log.insert(tk.END, "\n", tag)
            
        self.chat_log.see(tk.END)
        self.chat_log.config(state="disabled")

    def _insert_item(self, item, instant=True):
        # Sync version (helper)
        # Just calls async logic? No, cannot await here easily without loop.
        # Fallback to instant insertion.
        role = item.get("role")
        content = item.get("content")
        
        if role == "thought":
             return
        if role == "assistant" and content.strip().startswith("(Thought)"):
             return
             
        if role in ["log", "heartbeat"]:
             return
             
        if role == "system" and content.strip().startswith("User entered the room"):
             return
             
        tag = "system"
        header = "[System]"
        if role == "user": tag = "user"; header = "User"
        elif role == "assistant": 
            tag = "ai"
            header = self.controller.current_profile.name if self.controller.current_profile else "AI"
            
        self.chat_log.config(state="normal")
        self.chat_log.insert(tk.END, f"\n{header}: {content}\n", tag)
        self.chat_log.see(tk.END)
        self.chat_log.config(state="disabled")

    async def _typewriter_effect(self, text, tag, speed):
        for char in text:
            # Check if view destroyed
            if not self.winfo_exists(): break
            
            self.chat_log.insert(tk.END, char, tag)
            self.chat_log.see(tk.END)
            await asyncio.sleep(speed)
            # Force update to show char? Tkinter usually handles this in loop.

    def _on_send(self, event=None):
        text = self.entry.get().strip()
        if not text: return
        
        self.entry.delete(0, tk.END)
        # Thinking label handled by poll loop now
        
        # Async Send
        app = self.master.master
        if hasattr(app, 'loop'):
            app.loop.create_task(self.controller.handle_user_input(text))
