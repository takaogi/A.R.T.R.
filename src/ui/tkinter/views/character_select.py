
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import logging
import asyncio
from tkinter import filedialog
from typing import TYPE_CHECKING
from src.ui.tkinter.view_models.character import CharacterViewModel

if TYPE_CHECKING:
    from src.ui.tkinter.core.view_manager import ViewManager

class CharacterSelectView(ttk.Frame):
    def __init__(self, parent: 'ViewManager', controller):
        super().__init__(parent)
        self.controller = controller
        self.view_model = CharacterViewModel(controller)
        
        # Header
        ttk.Label(self, text="Select Character", font=("Segoe UI", 16, "bold")).pack(pady=20)
        
        # Main Layout: Listbox (Left) + Detail (Right)
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # List Panel
        list_frame = ttk.Labelframe(self.main_frame, text="Available Characters")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.char_listbox = tk.Listbox(list_frame, font=("Segoe UI", 12))
        self.char_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.char_listbox.bind("<<ListboxSelect>>", self._on_select)
        
        # Toolbar (moved to a separate frame at the bottom of the view)
        # The original btn_bar is replaced by a new button_frame for global actions
        
        # Detail Panel
        self.detail_frame = ttk.Labelframe(self.main_frame, text="Details", width=300)
        self.detail_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)
        self.detail_frame.pack_propagate(False) # Fixed width
        
        self.lbl_name = ttk.Label(self.detail_frame, text="", font=("Segoe UI", 14, "bold"))
        self.lbl_name.pack(pady=10)
        
        self.lbl_info = ttk.Label(self.detail_frame, text="Select a character to view details.\n(TODO: Show description)", wraplength=280)
        self.lbl_info.pack(pady=10, padx=10)
        
        # The launch button is now part of the global button_frame, so remove it from detail_frame
        # self.btn_launch = ttk.Button(self.detail_frame, text="Launch Chat", command=self._on_launch, state="disabled")
        # self.btn_launch.pack(side=tk.BOTTOM, pady=20, fill=tk.X, padx=20)
        
        # Global Action Buttons Frame
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Action Buttons (Standard Theme)
        ttk.Button(button_frame, text="新規作成", command=self._on_new_char).pack(side=tk.LEFT, padx=5)
                 
        ttk.Button(button_frame, text="CharX 取込", command=self._on_import_charx).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="削除", command=self._on_delete).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="戻る", command=self._on_back).pack(side=tk.RIGHT, padx=5)
                 
        # Launch Button (Accent Style if supported by theme, otherwise standard)
        self.btn_launch = ttk.Button(button_frame, text="起動", command=self._on_launch, state=tk.DISABLED, style="Accent.TButton")
        self.btn_launch.pack(side=tk.RIGHT, padx=5)
        
        # Initial Load
        self._refresh_list()

    def on_show(self):
        self._refresh_list()

    def _refresh_list(self):
        chars = self.view_model.scan_characters()
        self.char_listbox.delete(0, tk.END)
        for c in chars:
            self.char_listbox.insert(tk.END, c)

    def _on_select(self, event):
        selection = self.char_listbox.curselection()
        if selection:
            name = self.char_listbox.get(selection[0])
            self.view_model.select_character(name)
            
            # Update UI
            self.lbl_name.config(text=name)
            self.btn_launch.config(state="normal")
            # In future: Load profile meta to show description
        else:
            self.btn_launch.config(state="disabled")

    def _on_new_char(self):
        self.master.show_view("character_creator")

    def _on_back(self):
        self.master.show_view("dashboard")

    def _on_launch(self):
        if not self.view_model.selected_character:
            return
            
        # 1. Load Character (Async) via Task
        # Since we are in Tkinter event, we schedule async load
        self.btn_launch.config(state="disabled", text="Loading...")
        
        # We need to access the App's loop or use create_task on controller logic?
        # Controller calls are async.
        # We'll use self.controller (which creates tasks on loop?) No, controller methods are async def.
        # We use asyncio.create_task via App's loop reference if available, or just wrapping.
        # Since App passed `controller`, usually Views don't have direct loop access unless passed.
        # Assuming ViewManager -> App has loop.
        
        # Hack: self.master.master.loop ? 
        # ViewManager is parent. App is ViewManager's parent.
        app = self.master.master # Tk window (App)
        
        async def load_task():
            try:
                success = await self.view_model.load_character_to_engine()
                if success:
                    # Navigate to Chat
                    self.master.show_view("chat")
                else:
                    messagebox.showerror("Error", "Failed to load character.")
            except Exception as e:
                logging.error(f"Load failed: {e}")
                messagebox.showerror("Error", f"Load failed: {e}")
            finally:
                self.btn_launch.config(state="normal", text="Launch Chat")

        if hasattr(app, 'loop'):
            app.loop.create_task(load_task())
        else:
             logging.error("Could not find event loop.")

    def _on_import_charx(self):
        """Import .charx file."""
        path = filedialog.askopenfilename(
            title="Select Character File",
            filetypes=[("Character Files", "*.charx *.json"), ("All Files", "*.*")]
        )
        if not path:
            return

        # Explicit File ID
        file_id = simpledialog.askstring("Import Character", "Enter Target File Name (ID):\nThis will be the folder name (e.g. my_char_v1).", parent=self)
        if not file_id:
            return

        app = self.master.master
        
        # Status
        if hasattr(app, "status_bar"):
            app.status_bar.set_status("Importing character...", "busy")

        async def import_task():
            try:
                success = await self.view_model.import_character(path, file_id)
                if success:
                    messagebox.showinfo("Success", f"Character imported into '{file_id}'.")
                    self._refresh_list()
                else:
                    messagebox.showerror("Error", "Import failed.")
            except Exception as e:
                logging.error(f"Import error: {e}")
                messagebox.showerror("Error", f"Import error: {e}")
            finally:
                if hasattr(app, "status_bar"):
                    app.status_bar.set_status("Ready", "idle")

        if hasattr(app, 'loop'):
            app.loop.create_task(import_task())

    def _on_delete(self):
        selection = self.char_listbox.curselection()
        if not selection:
            return
        
        name = self.char_listbox.get(selection[0])
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{name}'?\nThis cannot be undone."):
            return
            
        success = self.view_model.delete_character(name)
        if success:
             self._refresh_list()
             self.lbl_name.config(text="")
             self.btn_launch.config(state="disabled")
             messagebox.showinfo("Deleted", f"Deleted '{name}'.")
        else:
             messagebox.showerror("Error", "Failed to delete character.")
