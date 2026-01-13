
import tkinter as tk
from tkinter import ttk
from typing import Dict, Type

class ViewManager(ttk.Frame):
    """
    Manages navigation between different views (Frames).
    """
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.current_view_name = None
        self.views: Dict[str, tk.Frame] = {}
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def register_view(self, name: str, view_class: Type[tk.Frame]):
        """Lazily stores view class, or instantiates?"""
        # For simplicity, we can instantiate on demand or preemptively.
        # Let's instantiate on demand to save resources?
        # But for simple app, instantiate all and raise is easier.
        pass

    def show_view(self, name: str):
        """Switches to the specified view."""
        if name in self.views:
            frame = self.views[name]
        else:
            # Lazy Load
            frame = self._create_view(name)
            if not frame:
                print(f"[UI] Error: View '{name}' not found.")
                return
            self.views[name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        frame.tkraise()
        # Trigger 'on_show' if view supports it
        if hasattr(frame, "on_show"):
            frame.on_show()
            
        self.current_view_name = name

    def _create_view(self, name: str):
        # Import views here to avoid circular deps at top level
        if name == "dashboard":
            from src.ui.tkinter.views.dashboard import DashboardView
            return DashboardView(self, self.controller)
        elif name == "character_select":
            from src.ui.tkinter.views.character_select import CharacterSelectView
            return CharacterSelectView(self, self.controller)
        elif name == "character_creator":
            from src.ui.tkinter.views.character_creator import CharacterCreatorView
            return CharacterCreatorView(self, self.controller)
        elif name == "chat":
            from src.ui.tkinter.views.chat import ChatView
            return ChatView(self, self.controller)
        return None
