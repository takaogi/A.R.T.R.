import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional
from src.utils.path_helper import get_data_dir

class CharacterSelector(tk.Toplevel):
    """
    Modal dialog to select a character from data/characters/
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Select Character")
        self.geometry("300x400")
        
        # Modify transient behavior: only if parent is visible
        if parent.state() == 'normal':
             self.transient(parent)
        
        self.grab_set()
        
        self.selected_char: Optional[str] = None
        
        # Layout
        lbl = ttk.Label(self, text="Available Characters:")
        lbl.pack(pady=10)
        
        # Listbox
        self.listbox = tk.Listbox(self, font=("Meiryo UI", 12))
        self.listbox.pack(expand=True, fill="both", padx=10, pady=5)
        self.listbox.bind("<Double-Button-1>", self.on_select)
        
        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=10)
        
        ok_btn = ttk.Button(btn_frame, text="Load", command=self.on_select)
        ok_btn.pack(side="right", padx=10)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.on_cancel)
        cancel_btn.pack(side="right", padx=10)
        
        self._populate_list()
        
        # Center the window
        self.center_window(parent)
        self.lift()
        self.attributes('-topmost', True)
        self.after_idle(self.attributes, '-topmost', False)

    def center_window(self, parent):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        
        # Check if parent is visible for centering precedence
        if parent.winfo_viewable():
            x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
            y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
        else:
            # Center on screen
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            
        self.geometry(f"+{x}+{y}")

    def _populate_list(self):
        char_dir = get_data_dir() / "characters"
        if not char_dir.exists():
            return
            
        # List .json files
        for f in char_dir.glob("*.json"):
            # Exclude folders or non-json
            if f.is_file():
                self.listbox.insert(tk.END, f.stem)

    def on_select(self, event=None):
        selection = self.listbox.curselection()
        if not selection:
            return
        
        self.selected_char = self.listbox.get(selection[0])
        self.destroy()

    def on_cancel(self):
        self.selected_char = None
        self.destroy()

def show_selection_dialog(parent: tk.Tk) -> Optional[str]:
    """
    Shows the dialog and returns the selected character name (or None).
    """
    dialog = CharacterSelector(parent)
    parent.wait_window(dialog)
    return dialog.selected_char
