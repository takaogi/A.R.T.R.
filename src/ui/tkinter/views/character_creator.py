
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog, filedialog
from src.ui.tkinter.view_models.character import CharacterViewModel
from src.ui.tkinter.utils.asset_loader import AssetLoader
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, Any
from src.foundation.logging import logger

if TYPE_CHECKING:
    from src.ui.tkinter.core.view_manager import ViewManager

class CharacterCreatorView(ttk.Frame):
    def __init__(self, parent: 'ViewManager', controller):
        super().__init__(parent)
        self.controller = controller
        self.view_model = CharacterViewModel(controller)
        
        # --- Header ---
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, pady=10)
        ttk.Label(header_frame, text="Character Creator", font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT, padx=20)
        
        button_frame = ttk.Frame(header_frame)
        button_frame.pack(side=tk.RIGHT, padx=20)
        
        ttk.Button(button_frame, text="キャラデータ読み込み", command=self._on_import_charx).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="エクスポート (.artrcc)", command=self._on_export_artrcc).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="保存", command=lambda: self._on_save(exit_after=False)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="保存して終了", command=lambda: self._on_save(exit_after=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="戻る", command=self._on_back).pack(side=tk.RIGHT)
        
        # --- AI Generation Section (Top) ---
        ai_frame = ttk.Labelframe(self, text="AI自動生成", padding=10)
        ai_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        ttk.Label(ai_frame, text="キャラの作成方針、あるいはWiki本文や設定資料を貼り付けてください:").pack(anchor="w")
        self.txt_prompt = scrolledtext.ScrolledText(ai_frame, height=3, font=("Segoe UI", 10))
        self.txt_prompt.pack(fill=tk.X, pady=5)
        
        self.btn_generate = ttk.Button(ai_frame, text="AIで生成 / 補正", command=self._on_generate)
        self.btn_generate.pack(anchor="e")
        
        # --- Tabbed Editor ---
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Track entries for saving
        self.entries: Dict[str, tk.Widget] = {}
        
        # Init Tabs
        self._init_tab_info()
        self._init_tab_persona()
        self._init_tab_narrative()
        self._init_tab_examples()
        self._init_tab_assets()

    def _init_tab_info(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="基本情報")
        
        self._create_field(frame, "名前", "name", height=1)
        self._create_field(frame, "別名 (カンマ区切り)", "aliases", height=1)
        self._create_field(frame, "外見 (Appearance)", "appearance", height=6)
        self._create_field(frame, "説明 / 概要 (Description)", "description", height=8)

    def _init_tab_persona(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="ペルソナ・背景")
        
        self._create_field(frame, "表層人格 (Surface Persona)", "surface_persona", height=4)
        self._create_field(frame, "深層人格 (Inner Persona)", "inner_persona", height=4)
        self._create_field(frame, "口調・特徴 (Speech Patterns)", "speech_patterns", height=4, help_text="一行につき一つのルール")
        self._create_field(frame, "背景ストーリー", "background_story", height=6)

    def _init_tab_narrative(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="シナリオ・世界観")
        
        self._create_field(frame, "世界観 (World Definition)", "world_definition", height=6)
        self._create_field(frame, "初期状況 (Initial Situation)", "initial_situation", height=6)
        self._create_field(frame, "最初のメッセージ (First Message)", "first_message", height=6)

    def _init_tab_examples(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="発話例")
        
        ttk.Label(frame, text="セリフ例 (一行につき一つ、または対話形式):").pack(anchor="w")
        self._create_field(frame, "", "speech_examples", height=20)

    def _init_tab_assets(self):
        """Asset Management Tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="立ち絵・アセット")
        
        # Layout: List (Left) | Preview (Right)
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Left Panel (List + Buttons)
        left_panel = ttk.Frame(paned, width=200)
        paned.add(left_panel, weight=1)
        
        # Guidance
        lbl_guide = ttk.Label(left_panel, text="【重要】命名規則:\n・デフォルト: 'main'\n・その他: 感情を表す英単語\n  (例: happy, angry)", font=("Segoe UI", 9), foreground="gray")
        lbl_guide.pack(fill=tk.X, padx=5, pady=5)
        
        self.asset_list = tk.Listbox(left_panel, font=("Segoe UI", 10))
        self.asset_list.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.asset_list.bind("<<ListboxSelect>>", self._on_select_asset)
        
        btn_bar = ttk.Frame(left_panel)
        btn_bar.pack(fill=tk.X)
        ttk.Button(btn_bar, text="画像を追加...", command=self._on_add_asset).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btn_bar, text="削除", command=self._on_delete_asset).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btn_bar, text="更新", command=self._refresh_assets).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Right Panel (Preview)
        right_panel = ttk.Frame(paned)
        paned.add(right_panel, weight=3)
        
        self.preview_canvas = tk.Canvas(right_panel, bg="#202020")
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        self.preview_img = None # Ref

    # --- Helpers ---
    def _create_field(self, parent, label: str, key: str, height=1, help_text=""):
        if label:
            ttk.Label(parent, text=label + ":").pack(anchor="w", pady=(5, 0))
        if help_text:
            ttk.Label(parent, text=help_text, font=("Segoe UI", 8), foreground="gray").pack(anchor="w")
            
        if height > 1:
            widget = scrolledtext.ScrolledText(parent, height=height, font=("Segoe UI", 10))
        else:
            widget = ttk.Entry(parent, font=("Segoe UI", 10))
            
        widget.pack(fill=tk.X, pady=(2, 5))
        self.entries[key] = widget

    def _set_field(self, key: str, value: Any):
        if key not in self.entries:
            return
            
        widget = self.entries[key]
        
        # Convert List -> Text
        if isinstance(value, list) and isinstance(widget, scrolledtext.ScrolledText):
            value = "\n".join([str(v) for v in value])
        elif isinstance(value, list):
             value = ", ".join([str(v) for v in value])
             
        if value is None: value = ""
        
        if isinstance(widget, ttk.Entry):
            widget.delete(0, tk.END)
            widget.insert(0, str(value))
        else:
            widget.delete("1.0", tk.END)
            widget.insert("1.0", str(value))

    def _get_field(self, key: str) -> Any:
        # Returns raw string (or list for specific fields)
        if key not in self.entries:
            return ""
            
        widget = self.entries[key]
        val = ""
        if isinstance(widget, ttk.Entry):
            val = widget.get()
        else:
            val = widget.get("1.0", tk.END).strip()
            
        return val

    # --- Actions ---
    def _on_back(self):
        self.master.show_view("character_select")

    def _on_generate(self):
        text = self.txt_prompt.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Input Required", "Please enter description.")
            return

        self.btn_generate.config(state="disabled", text="Working...")
        app = self.master.master
        
        # Status Bar Update (Show Model Name)
        model_name = self.view_model.get_model_name_for_strategy("character_generate")
        if hasattr(app, "status_bar"):
            app.status_bar.set_status(f"Generating Profile... (Model: {model_name})", "busy")

        async def task():
            try:
                # 1. Gather Current Context (Scrape UI)
                context = {}
                
                # Helper: Only add if not empty
                def add_if_val(k):
                    val = self._get_field(k)
                    if val:
                        # Convert list-like strings to lists for context?
                        if k in ["aliases", "speech_examples", "speech_patterns"]:
                            # Attempt split
                            if "\n" in val:
                                val = [x.strip() for x in val.split("\n") if x.strip()]
                            elif "," in val and k == "aliases":
                                val = [x.strip() for x in val.split(",") if x.strip()]
                            else:
                                val = [val] if val.strip() else []
                        
                        if val:
                            context[k] = val

                # Scrape all known fields
                for key in ["name", "aliases", "appearance", "description", 
                           "surface_persona", "inner_persona", "speech_patterns", 
                           "background_story", "world_definition", "initial_situation", 
                           "first_message", "speech_examples"]:
                    add_if_val(key)

                # Pass context as 'existing_data' to Service
                success = await self.view_model.generate_draft(text, current_data=context)
                if success:
                    self._populate_ui()
                    messagebox.showinfo("Done", "Profile Generated/Refined.")
                else:
                    messagebox.showerror("Error", "Generation failed.")
            except Exception as e:
                logger.error(f"Gen Error: {e}")
                messagebox.showerror("Error", f"{e}")
            finally:
                self.btn_generate.config(state="normal", text="AIで生成 / 補正")
                # Status Reset
                if hasattr(app, "status_bar"):
                     app.status_bar.set_status("Ready", "idle")
        
        if hasattr(app, "loop"):
             app.loop.create_task(task())

    def _on_export_artrcc(self):
        """Exports current character to .artrcc"""
        name = self._get_field("name")
        if not name:
             messagebox.showwarning("Warning", "Please enter a name first.")
             return

        # 1. Ask for Save Path
        initial_file = f"{name}.artrcc"
        initial_file = "".join([c for c in initial_file if c.isalnum() or c in (' ', '-', '_', '.')]).strip()
        
        path = filedialog.asksaveasfilename(
            defaultextension=".artrcc",
            filetypes=[("A.R.T.R Character Card", "*.artrcc")],
            initialfile=initial_file,
            title="Export Character"
        )
        if not path: return

        if not self.view_model.current_file_id:
             if messagebox.askyesno("Save Required", "Character must be saved internally before exporting.\nSave now?"):
                 self._on_save(exit_after=False)
                 if not self.view_model.current_file_id:
                     return
             else:
                 return

        file_id = self.view_model.current_file_id
        
        try:
            success = self.view_model.export_character(file_id, path)
            if success:
                messagebox.showinfo("Success", f"Exported to {path}")
            else:
                messagebox.showerror("Error", "Export failed check logs.")
        except Exception as e:
            messagebox.showerror("Error", f"Export Error: {e}")

    def _on_import_charx(self):
        path = filedialog.askopenfilename(
            title="Import Base Character",
            filetypes=[("Character Files", "*.charx *.json *.artrcc"), ("All Files", "*.*")]
        )
        if not path: return
        
        file_id = simpledialog.askstring("Import Character", "Enter Target File Name (ID):\nThis will be the folder name (e.g. my_char_v1).", parent=self)
        if not file_id:
            return

        app = self.master.master
        
        # Status
        if hasattr(app, "status_bar"):
            app.status_bar.set_status("Importing CharX...", "busy")

        async def task():
            try:
                res = await self.view_model.import_character(path, file_id)
                if res:
                    self._populate_ui()
                    self._refresh_assets() # Update asset tab
                    messagebox.showinfo("Success", f"Character Data Imported into '{file_id}'.")
                else:
                    messagebox.showerror("Error", "Import Failed.")
            except Exception as e:
                logger.error(f"Import Error: {e}")
                messagebox.showerror("Error", f"{e}")
            finally:
                if hasattr(app, "status_bar"):
                    app.status_bar.set_status("Ready", "idle")

        if hasattr(app, "loop"):
             app.loop.create_task(task())

    def _populate_ui(self):
        p = self.view_model.draft_profile
        if not p: return
        
        self._set_field("name", p.name)
        self._set_field("aliases", p.aliases)
        self._set_field("appearance", p.appearance)
        self._set_field("description", p.description or p.surface_persona) # Fallback? No, Schema has desc.
        
        self._set_field("surface_persona", p.surface_persona)
        self._set_field("inner_persona", p.inner_persona)
        self._set_field("speech_patterns", p.speech_patterns)
        self._set_field("background_story", p.background_story)
        
        self._set_field("world_definition", p.world_definition)
        self._set_field("initial_situation", p.initial_situation)
        self._set_field("first_message", p.first_message)
        
        self._set_field("speech_examples", p.speech_examples)

    def _on_save(self, exit_after=True):
        name = self._get_field("name")
        if not name:
            messagebox.showwarning("Error", "Name is required.")
            return

        # Update Draft Object
        if not self.view_model.draft_profile:
             from src.modules.character.schema import CharacterProfile
             self.view_model.draft_profile = CharacterProfile(name=name)

        p = self.view_model.draft_profile
        p.name = name
        
        p.aliases = [x.strip() for x in self._get_field("aliases").split(",") if x.strip()]
        p.speech_patterns = [x for x in self._get_field("speech_patterns").split("\n") if x.strip()]
        p.speech_examples = [x for x in self._get_field("speech_examples").split("\n") if x.strip()]
        
        p.appearance = self._get_field("appearance")
        p.description = self._get_field("description")
        p.surface_persona = self._get_field("surface_persona")
        p.inner_persona = self._get_field("inner_persona")
        p.background_story = self._get_field("background_story")
        p.world_definition = self._get_field("world_definition")
        p.initial_situation = self._get_field("initial_situation")
        p.first_message = self._get_field("first_message")

        initial = self.view_model.current_file_id or "".join(c for c in name if c.isalnum() or c in ('_', '-')).strip()
        
        if not self.view_model.current_file_id:
             file_id = simpledialog.askstring("Save Character", "Enter File Name (ID):\nThis determines the folder name.", initialvalue=initial, parent=self)
             if not file_id:
                 return
        else:
             file_id = self.view_model.current_file_id

        if self.view_model.save_draft(file_id):
            messagebox.showinfo("Saved", f"Character '{name}' saved as '{file_id}'.")
            if exit_after:
                self.master.show_view("character_select")
        else:
            messagebox.showerror("Error", "Save failed.")

    # --- Asset Logic ---
    def _get_asset_dir(self) -> Path:
        p = self.view_model.draft_profile
        if p and p.name:
             if self.view_model.current_file_id:
                 from src.foundation.paths.manager import PathManager
                 pm = PathManager.get_instance()
                 return pm.get_characters_dir() / self.view_model.current_file_id / "assets"

             from src.foundation.paths.manager import PathManager
             pm = PathManager.get_instance()
             safe_name = "".join([c for c in p.name if c.isalnum() or c in (' ', '-', '_')]).strip()
             return pm.get_characters_dir() / safe_name / "assets"
        return None

    def _refresh_assets(self):
        self.asset_list.delete(0, tk.END)
        path = self._get_asset_dir()
        if not path or not path.exists():
            return

        for f in path.glob("*"):
            if f.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
                self.asset_list.insert(tk.END, f.name)

    def _on_select_asset(self, event):
        sel = self.asset_list.curselection()
        if not sel: return
        fname = self.asset_list.get(sel[0])
        path = self._get_asset_dir() / fname
        
        # Display
        img = AssetLoader.load_image(path, size=(400, 600)) # Fit preview
        self.preview_canvas.delete("all")
        if img:
            self.preview_img = img
            # Center
            w = self.preview_canvas.winfo_width()
            h = self.preview_canvas.winfo_height()
            self.preview_canvas.create_image(w//2, h//2, image=img)
        else:
            self.preview_canvas.create_text(100, 100, text="Load Error", fill="red")

    def _on_add_asset(self):
        path = self._get_asset_dir()
        if not path:
             messagebox.showwarning("Warning", "Please Save Character or Import first to establish asset directory.")
             return
             
        src = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.webp")])
        if not src: return
        
        name = simpledialog.askstring("Asset Name", "Enter Expression Name (e.g. 'smile', 'angry', 'default'):")
        if not name: return
        
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            
        ext = Path(src).suffix
        target = path / f"{name}{ext}"
        
        try:
            shutil.copy2(src, target)
            self._refresh_assets()
            messagebox.showinfo("Success", f"Asset added: {name}{ext}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add asset: {e}")

    def _on_delete_asset(self):
        sel = self.asset_list.curselection()
        if not sel: return
        fname = self.asset_list.get(sel[0])
        path = self._get_asset_dir() / fname
        
        if messagebox.askyesno("Confirm", f"Delete {fname}?"):
            try:
                os.remove(path)
                self.preview_canvas.delete("all")
                self._refresh_assets()
            except Exception as e:
                messagebox.showerror("Error", f"Delete failed: {e}")
