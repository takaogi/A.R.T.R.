
import tkinter as tk
from tkinter import ttk
from src.ui.tkinter.utils.asset_loader import AssetLoader

class TachieDisplay(ttk.Frame):
    """
    Displays the character's standing picture.
    Updates based on expression state.
    """
    def __init__(self, parent, char_name: str = None):
        super().__init__(parent)
        self.char_name = char_name
        self.current_expression = "default"
        
        self.canvas = tk.Canvas(self, bg="#202020", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.image_item = None
        self._current_tk_img = None
        
        # Bind resize
        self.bind("<Configure>", self._on_resize)

    def set_character(self, profile, directory_name: str = None):
        """
        Sets the character profile to display.
        """
        # Use explicit directory name if available, else fallback to profile name
        self.char_name = directory_name if directory_name else profile.name
        self.asset_map = profile.asset_map
        self.update_expression("default")

    def update_expression(self, expression: str):
        if not self.char_name:
            return
            
        self.current_expression = expression
        self._redraw()

    def _redraw(self):
        if not self.char_name:
            return
            
        # Get Canvas Height
        height = self.winfo_height()
        if height < 100: height = 600
        
        img = AssetLoader.get_tachie(self.char_name, self.current_expression, asset_map=self.asset_map, max_height=height)
        
        self.canvas.delete("all")
        if img:
            self._current_tk_img = img # Keep Reference
            # Center image
            width = self.winfo_width()
            x = width // 2
            y = height # Anchor bottom? Or Center?
            # Usually Tachie is anchored bottom.
            
            self.canvas.create_image(x, height, image=img, anchor="s")
        else:
            # Placeholder text
            self.canvas.create_text(self.winfo_width()//2, height//2, text=f"[{self.char_name}]\n({self.current_expression})", fill="white")

    def _on_resize(self, event):
        # Debounce?
        self._redraw()
