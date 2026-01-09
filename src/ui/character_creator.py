import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json
import threading
import asyncio
import shutil
from pathlib import Path
from src.utils.path_helper import get_data_dir
from src.utils.logger import logger
from src.utils.llm_client import LLMClient
from src.config import settings
from src.schemas.character import CharacterProfile
from src.config.reaction_styles import REACTION_STYLE_DB, get_options_for_anchor

# Placeholder Text Helper
class PlaceholderEntry(tk.Entry):
    def __init__(self, container, placeholder, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = 'grey'
        self.default_fg_color = 'black' # Default for tk.Entry

        # Bind events
        self.bind("<FocusIn>", self._clear_placeholder)
        self.bind("<FocusOut>", self._add_placeholder)

        # Initialize
        self['fg'] = self.placeholder_color
        self.insert(0, self.placeholder)

    def _clear_placeholder(self, e):
        if self.get() == self.placeholder and self['fg'] == self.placeholder_color:
            self.delete(0, tk.END)
            self['fg'] = self.default_fg_color

    def _add_placeholder(self, e=None):
        if not self.get():
            self.insert(0, self.placeholder)
            self['fg'] = self.placeholder_color

    def get_actual_value(self):
        val = self.get()
        if val == self.placeholder and self['fg'] == self.placeholder_color:
            return ""
        return val

    def set_value(self, value):
        self.delete(0, tk.END)
        self['fg'] = self.default_fg_color
        self.insert(0, value)
        if not value:
            self._add_placeholder()


class PlaceholderText(tk.Text):
    def __init__(self, container, placeholder, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = 'grey'
        self.default_fg_color = self['fg']

        self.bind("<FocusIn>", self._clear_placeholder)
        self.bind("<FocusOut>", self._add_placeholder)

        self._add_placeholder()

    def _clear_placeholder(self, e):
        if self.get("1.0", "end-1c") == self.placeholder and self['fg'] == self.placeholder_color:
            self.delete("1.0", tk.END)
            self['fg'] = self.default_fg_color

    def _add_placeholder(self, e=None):
        if not self.get("1.0", "end-1c"):
            self.insert("1.0", self.placeholder)
            self['fg'] = self.placeholder_color

    def get_actual_value(self):
        val = self.get("1.0", "end-1c")
        if val == self.placeholder and self['fg'] == self.placeholder_color:
            return ""
        return val.strip()

    def set_value(self, value):
        self.delete("1.0", tk.END)
        self['fg'] = self.default_fg_color
        self.insert("1.0", value)
        if not value:
            self._add_placeholder()

class CharacterCreatorWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("A.R.T.R. Character Creator V2")
        self.root.geometry("1000x900")
        
        self.data_dir = get_data_dir() / "characters"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.entries = {}
        self.vars = {} # New: store tk variables for non-entry widgets
        self.dialogue_rows = []
        
        self._init_ui()

    def _init_ui(self):
        # Main container with scrollbar
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # Create window inside canvas
        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Ensure frame fits canvas width
        def _configure_frame(event):
            canvas.itemconfig(window_id, width=event.width)
        
        canvas.bind("<Configure>", _configure_frame)

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.canvas = canvas # Store for scrolling
        
        # Mousewheel scrolling
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        self.root.bind_all("<MouseWheel>", _on_mousewheel)
        
        self.scrollable_frame = scrollable_frame

        # --- Basic Fields ---
        self._create_header(scrollable_frame, "Basic Information (基本情報)")
        self._create_entry_field(scrollable_frame, "Name (キャラクター名)", "name", "キャラクターの表示名・識別子。")
        self._create_text_field(scrollable_frame, "Description (性格・容姿・背景)", "description", "性格、容姿、背景など。\nCore Memoryの 'Persona' ブロックとして常に参照されます。")
        self._create_text_field(scrollable_frame, "Scenario (シチュエーション・ユーザーとの関係)", "scenario", "現在の状況やユーザーとの関係性。\nCore Memoryの 'Scenario' ブロックとして参照されます。")
        self._create_text_field(scrollable_frame, "First Message (最初の挨拶)", "first_message", "チャット開始時にユーザーに送信される最初のメッセージ。")

        # --- Dialogue Editor ---
        self._create_header(scrollable_frame, "Example Dialogue (会話例: <START>で区切り, {{user}} / {{char}} 使用)")
        self.dialogue_frame = ttk.Frame(scrollable_frame)
        self.dialogue_frame.pack(fill=tk.X, padx=10, pady=5)
        
        add_dia_btn = ttk.Button(self.dialogue_frame, text="+ Add Interaction (会話追加)", command=self._add_dialogue_row)
        add_dia_btn.pack(anchor="w", pady=5)

        # --- System & Reflex ---
        self._create_header(scrollable_frame, "System & Reflex (高度な指示)")
        self._create_text_field(scrollable_frame, "Post History Instructions (追加システム指示)", "system_prompt", "AIへの技術的な指示。\nシステムプロンプトの末尾に追加されます。")
        self._create_text_field(scrollable_frame, "Reflex Examples (反射的返答例 - ニュートラル)", "reflex_examples", "Reflex Layer（反射層）が使用する応答パターン。")
        self._create_entry_field(scrollable_frame, "White Room Path", "white_room_path", "data/white_room")
        self._create_entry_field(scrollable_frame, "Default Length", "default_length", "例: 1~2 sentences")
        
        self.set_value("white_room_path", "data/white_room")
        self.set_value("default_length", "1~2 sentences")

        # --- Advanced Settings (Collapsible) ---
        adv_frame_container = ttk.Frame(scrollable_frame)
        adv_frame_container.pack(fill=tk.X, pady=10)
        
        self.show_adv = tk.BooleanVar(value=False)
        adv_toggle_btn = ttk.Checkbutton(adv_frame_container, text="Show Advanced Settings (Manual Override)", variable=self.show_adv, command=lambda: self._toggle_advanced(adv_frame))
        adv_toggle_btn.pack(anchor="w", padx=10)
        
        adv_frame = ttk.Frame(adv_frame_container, padding=10, relief=tk.GROOVE)
        self._create_advanced_settings(adv_frame)
        self.adv_frame_ref = adv_frame

        # --- Action Buttons ---
        btn_frame = ttk.Frame(scrollable_frame, padding=10)
        btn_frame.pack(fill=tk.X, pady=20)
        
        # Load Sample
        sample_btn = ttk.Button(btn_frame, text="Load Sample (A.R.T.R. Classic)", command=self._load_sample)
        sample_btn.pack(fill=tk.X, pady=5)

        # AI Assist
        self.ai_btn = ttk.Button(btn_frame, text="✨ AI Assist (Auto Fill & Complete)", command=self.on_ai_assist)
        self.ai_btn.pack(fill=tk.X, pady=5)

        # Save/Load
        action_frame = ttk.Frame(btn_frame)
        action_frame.pack(fill=tk.X, pady=5)
        ttk.Button(action_frame, text="Save Character", command=self.save_character).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Button(action_frame, text="Load Character", command=self.load_character).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # Status
        self.status_var = tk.StringVar()
        ttk.Label(btn_frame, textvariable=self.status_var, foreground="blue").pack(side=tk.BOTTOM, pady=5)

    def _create_advanced_settings(self, parent):
        # 1. Pacemaker
        lbl = ttk.LabelFrame(parent, text="Pacemaker (Spontaneity)", padding=5)
        lbl.pack(fill=tk.X, pady=5)
        
        f1 = ttk.Frame(lbl)
        f1.pack(fill=tk.X)
        ttk.Label(f1, text="Base Interval (sec) (10-600):").pack(side=tk.LEFT)
        self._create_var_entry(f1, "pm_interval", 60)
        
        f2 = ttk.Frame(lbl)
        f2.pack(fill=tk.X)
        ttk.Label(f2, text="Variance (0.0-1.0):").pack(side=tk.LEFT)
        self._create_scale(f2, "pm_variance", 0.0, 1.0, 0.2)

        # 2. VAD Baseline
        lbl_vad = ttk.LabelFrame(parent, text="VAD Baseline (-1.0 to 1.0)", padding=5)
        lbl_vad.pack(fill=tk.X, pady=5)

        self._create_scale_row(lbl_vad, "Valence (Sad-Happy)", "vad_b_v", -1.0, 1.0, 0.0)
        self._create_scale_row(lbl_vad, "Arousal (Calm-Excited)", "vad_b_a", -1.0, 1.0, 0.0)
        self._create_scale_row(lbl_vad, "Dominance (Weak-Strong)", "vad_b_d", -1.0, 1.0, 0.0)

        # 3. VAD Volatility
        lbl_vol = ttk.LabelFrame(parent, text="VAD Volatility (Sensitivity 0.1 to 3.0)", padding=5)
        lbl_vol.pack(fill=tk.X, pady=5)
        self._create_scale_row(lbl_vol, "Valence Volatility", "vad_v_v", 0.1, 3.0, 1.0)
        self._create_scale_row(lbl_vol, "Arousal Volatility", "vad_v_a", 0.1, 3.0, 1.0)
        self._create_scale_row(lbl_vol, "Dominance Volatility", "vad_v_d", 0.1, 3.0, 1.0)

        # 4. Reaction Styles
        lbl_react = ttk.LabelFrame(parent, text="Reaction Styles (Overrides)", padding=5)
        lbl_react.pack(fill=tk.X, pady=5)
        
        # Unique Anchors
        try:
             unique_anchors = sorted(list(set(v.anchor for v in REACTION_STYLE_DB.values())))
        except:
             unique_anchors = []

        for anchor in unique_anchors:
            f = ttk.Frame(lbl_react)
            f.pack(fill=tk.X, pady=2)
            ttk.Label(f, text=f"{anchor}:", width=20).pack(side=tk.LEFT)
            
            options = ["(Auto)"] + get_options_for_anchor(anchor)
            var = tk.StringVar(value="(Auto)")
            cb = ttk.Combobox(f, textvariable=var, values=options, state="readonly")
            cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.vars[f"style_{anchor}"] = var

    def _create_var_entry(self, parent, key, default):
        var = tk.DoubleVar(value=default) # Using double for flexibility
        ent = ttk.Entry(parent, textvariable=var, width=10)
        ent.pack(side=tk.LEFT, padx=5)
        self.vars[key] = var
        return ent

    def _create_scale(self, parent, key, from_, to, default):
        var = tk.DoubleVar(value=default)
        s = ttk.Scale(parent, from_=from_, to=to, variable=var, orient=tk.HORIZONTAL)
        s.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        # Value Label
        l = ttk.Label(parent, text=f"{default:.2f}", width=5)
        l.pack(side=tk.LEFT)
        # Update label on change
        def update_lbl(v):
            l.config(text=f"{float(v):.2f}")
        s.configure(command=update_lbl)
        self.vars[key] = var
        return s

    def _create_scale_row(self, parent, label, key, from_, to, default):
        f = ttk.Frame(parent)
        f.pack(fill=tk.X)
        ttk.Label(f, text=label, width=20).pack(side=tk.LEFT)
        self._create_scale(f, key, from_, to, default)

    def _create_header(self, parent, text):
        lbl = ttk.Label(parent, text=text, font=("Meiryo", 10, "bold"), foreground="#444")
        lbl.pack(anchor="w", pady=(15, 5))

    def _create_entry_field(self, parent, label, key, placeholder):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text=label, width=25, anchor="w").pack(side=tk.LEFT, anchor="n", pady=3)
        entry = PlaceholderEntry(frame, placeholder)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entries[key] = entry
        return entry

    def _create_text_field(self, parent, label, key, placeholder, height=4):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text=label, width=25, anchor="w").pack(side=tk.LEFT, anchor="n", pady=3)
        text = PlaceholderText(frame, placeholder, height=height)
        text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entries[key] = text
        return text

    def _add_dialogue_row(self, user_text="", char_text=""):
        frame = ttk.Frame(self.dialogue_frame)
        frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(frame, text="User:").pack(side=tk.LEFT)
        user_ent = ttk.Entry(frame)
        user_ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        if user_text: user_ent.insert(0, user_text)
        
        ttk.Label(frame, text="Char:").pack(side=tk.LEFT)
        char_ent = ttk.Entry(frame)
        char_ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        if char_text: char_ent.insert(0, char_text)
        
        del_btn = ttk.Button(frame, text="X", width=3, command=lambda: self._remove_dialogue_row(frame))
        del_btn.pack(side=tk.LEFT, padx=2)

        self.dialogue_rows.append({"frame": frame, "user": user_ent, "char": char_ent})

    def _remove_dialogue_row(self, frame):
        frame.destroy()
        self.dialogue_rows = [row for row in self.dialogue_rows if row["frame"] != frame]

    def _clear_dialogue_rows(self):
        for row in self.dialogue_rows:
            row["frame"].destroy()
        self.dialogue_rows = []

    def _toggle_advanced(self, frame):
        if self.show_adv.get():
            frame.pack(fill=tk.X, expand=True)
        else:
            frame.pack_forget()

    def get_value(self, key):
        if key in self.entries:
            return self.entries[key].get_actual_value()
        if key in self.vars:
            return self.vars[key].get()
        return None

    def set_value(self, key, value):
        if key in self.entries:
            self.entries[key].set_value(str(value))
        elif key in self.vars:
            try:
                self.vars[key].set(value)
            except:
                pass # Ignore type mismatch or invalid value for now

    def get_structured_dialogue_text(self):
        # Convert rows to RisuAI format string
        lines = []
        for row in self.dialogue_rows:
            u = row["user"].get().strip()
            c = row["char"].get().strip()
            if u or c:
                lines.append("<START>")
                if u: lines.append(f"{{{{user}}}}: {u}")
                if c: lines.append(f"{{{{char}}}}: {c}")
        return "\n".join(lines)

    def set_structured_dialogue_from_text(self, text):
        self._clear_dialogue_rows()
        if not text: return

        # Robust Parsing: Handle case where LLM forgets <START> but provides content
        # Normalize newlines
        text = text.replace("\r\n", "\n")
        
        blocks = text.split("<START>")
        # If no <START> found, treating whole text as one block might be safer if it contains pattern
        if len(blocks) == 1 and ("{{user}}" in text or "{{char}}" in text):
             # Try to split by double newline as fallback if multiple pairs exist
             potential_blocks = text.split("\n\n")
             if len(potential_blocks) > 1:
                 blocks = potential_blocks
        
        count = 0 
        for block in blocks:
            if not block.strip(): continue
            user_msg = ""
            char_msg = ""
            
            # Simple line parser
            for line in block.split('\n'):
                line = line.strip()
                if not line: continue
                # Relaxed matching
                if line.lower().startswith("{{user}}") or line.lower().startswith("user:"):
                    parts = line.split(":", 1)
                    if len(parts) > 1: user_msg = parts[1].strip()
                elif line.lower().startswith("{{char}}") or line.lower().startswith("char:"):
                    parts = line.split(":", 1)
                    if len(parts) > 1: char_msg = parts[1].strip()
            
            if user_msg or char_msg:
                self._add_dialogue_row(user_msg, char_msg)
                count += 1
        
        logger.info(f"Parsed {count} dialogue rows from AI output.")

    def _load_sample(self):
        messagebox.showinfo("Sample", "Sample character data is currently under construction.\n(Functionality preserved for future update)")

    def on_ai_assist(self):
        # 0. Pre-condition: If dialogue is empty, add 5 placeholder rows
        # This converts a "Generation" task into a "Completion" task (Partial Fill)
        if not self.dialogue_rows:
            logger.info("No dialogue rows found. Adding 5 empty rows for AI to fill.")
            for _ in range(5):
                self._add_dialogue_row()
            # Force UI update so user sees the slots appear
            self.root.update_idletasks()

        # 1. Gather Context (Base)
        context = {key: self.get_value(key) for key in self.entries}
        
        # 2. Analyze Dialogue State
        dia_lines = []
        has_content = False
        has_missing = False
        
        for row in self.dialogue_rows:
            u = row["user"].get().strip()
            c = row["char"].get().strip()
            
            # Format for LLM Context
            # Using <MISSING> to signal gaps
            block = ["<START>"]
            if u:
                block.append(f"{{{{user}}}}: {u}")
                has_content = True
            else:
                block.append(f"{{{{user}}}}: <MISSING>")
                has_missing = True
                
            if c:
                block.append(f"{{{{char}}}}: {c}")
                has_content = True
            else:
                block.append(f"{{{{char}}}}: <MISSING>")
                has_missing = True
            
            dia_lines.append("\n".join(block))
        
        if not has_content:
             # This happens if we just added 5 empty rows
             dia_state = "PARTIAL" # Treat as partial so we use the fill-in logic
        elif has_missing:
            dia_state = "PARTIAL"
        else:
            dia_state = "FULL"
        
        context["example_dialogue"] = "\n\n".join(dia_lines) if dia_lines else ""
        
        # 3. Determine Dialogue Instruction
        if dia_state == "PARTIAL":
            dia_instruction = "IMPORTANT: The 'example_dialogue' provided contains <MISSING> placeholders. Replace ALL <MISSING> tags with appropriate dialogue to complete the examples. Keep existing text exactly as is. Do NOT add new conversation blocks beyond the provided structure."
        else: # FULL
            dia_instruction = "IMPORTANT: For 'example_dialogue', the user has already provided a complete set. RETURN THE INPUT 'example_dialogue' EXACTLY AS IS. DO NOT MODIFY IT."

        # Ask for optional instructions
        instructions = simpledialog.askstring("AIへの指示", "AIへの追加指示を入力してください (任意):\n(例: 'ツンデレにして', '関西弁を使って')")
        
        logger.info(f"Starting AI Assist. State: {dia_state}. Instructions: {instructions}")
        
        self.status_var.set("AI is thinking... (Please wait)")
        self.ai_btn.config(state=tk.DISABLED)
        # Pass dia_instruction explicitly
        threading.Thread(target=self._run_async_generation, args=(context, instructions, dia_instruction), daemon=True).start()

    def _run_async_generation(self, context, instructions, dia_instruction):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            profile = loop.run_until_complete(self._generate_profile(context, instructions, dia_instruction))
            loop.close()
            self.root.after(0, self._apply_profile, profile)
        except Exception as e:
            self.root.after(0, self._show_error, str(e))

    async def _generate_profile(self, context, instructions, dia_instruction) -> CharacterProfile:
        logger.info(f"Requesting LLM generation (Model: {settings.OPENAI_MODEL_CORE}, Effort: {settings.REASONING_EFFORT_CORE})")
        
        prompt = "You are an expert AI character designer. Complete the character profile based on the provided partial information.\n"
        prompt += "If fields are empty, infer them creatively.\n"
        prompt += "IMPORTANT: Output ALL fields strictly in JAPANESE (日本語).\n"
        prompt += "IMPORTANT: For 'name', use an ORIGINAL name. DO NOT use names of real people or existing copyrighted characters (e.g. do not use 'Onodera Yui', 'Ayanami Rei').\n"
        prompt += "IMPORTANT: For 'white_room_path', preserve the default 'data/white_room'. Do NOT change it unless instructed.\n"
        prompt += "IMPORTANT: For 'reflex_examples', provide short, neutral, reactive phrases (e.g., 'Hmm', 'I see', 'Oh') suitable for a reflex layer. Do NOT include complex opinions or strong affirmations/denials unless specified.\n"
        
        # Dynamic Dialogue Instruction
        prompt += f"{dia_instruction}\n"
        
        if instructions:
            prompt += f"USER INSTRUCTIONS: {instructions}\n"
            
        prompt += "\nCurrent Fields:\n"
        for k, v in context.items():
            prompt += f"- {k}: {v}\n"

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Fill in the missing details in Japanese."}
        ]

        return await LLMClient.request_structured(
            messages=messages,
            model=settings.OPENAI_MODEL_CORE,
            response_model=CharacterProfile,
            reasoning_effort=settings.REASONING_EFFORT_CORE
        )

    def _apply_profile(self, profile: CharacterProfile):
        self.status_var.set("Generation complete!")
        self.ai_btn.config(state=tk.NORMAL)
        
        if not profile: return
        
        data = profile.model_dump()
        for key, value in data.items():
            # Safety: Do not overwrite White Room Path if it's already set to a valid path
            if key == "white_room_path":
                current_val = self.get_value("white_room_path")
                if current_val and "data" in current_val: # Simple heuristic or just trust current
                     continue # Skip overwriting
                     
            if key == "example_dialogue":
                self.set_structured_dialogue_from_text(value)
            else:
                self.set_value(key, value)
                
        messagebox.showinfo("AI Assist", "Character profile updated based on AI generation.")

    def _show_error(self, msg):
        self.status_var.set("Error occurred.")
        self.ai_btn.config(state=tk.NORMAL)
        logger.error(f"AI Assist Error: {msg}")
        messagebox.showerror("AI Error", f"Failed to generate profile:\n{msg}")

    def save_character(self):
        name = self.get_value("name")
        if not name:
            messagebox.showerror("Error", "Name is required.")
            return

        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_name: safe_name = "character"
        
        # Prepare Character Directory
        char_dir = self.data_dir / safe_name
        char_dir.mkdir(parents=True, exist_ok=True)
        
        # Handle White Room Path
        raw_wr = self.get_value("white_room_path")
        final_wr = raw_wr
        
        # If it's a local file that exists, copy it to character storage
        wr_path = Path(raw_wr)
        if wr_path.is_file() and not "{{char_name}}" in raw_wr:
            try:
                wr_dest_dir = char_dir / "white_room"
                wr_dest_dir.mkdir(exist_ok=True)
                dest_file = wr_dest_dir / wr_path.name
                shutil.copy2(wr_path, dest_file)
                logger.info(f"Copied White Room asset to {dest_file}")
                
                # Update path to use placeholder
                final_wr = f"{{{{char_name}}}}/white_room/{wr_path.name}"
            except Exception as e:
                logger.error(f"Failed to copy white room asset: {e}")
        
        # Basic Data
        data = {key: self.get_value(key) for key in self.entries}
        data["white_room_path"] = final_wr
        data["example_dialogue"] = self.get_structured_dialogue_text()
        
        # Construct System Params
        data["system_params"] = {
            "pacemaker": {
                "base_interval_sec": int(self.get_value("pm_interval") or 60),
                "variance": float(self.get_value("pm_variance") or 0.2)
            },
            "vad_baseline": {
                "valence": float(self.get_value("vad_b_v") or 0.0),
                "arousal": float(self.get_value("vad_b_a") or 0.0),
                "dominance": float(self.get_value("vad_b_d") or 0.0)
            },
            "vad_volatility": {
                "valence": float(self.get_value("vad_v_v") or 1.0),
                "arousal": float(self.get_value("vad_v_a") or 1.0),
                "dominance": float(self.get_value("vad_v_d") or 1.0)
            }
        }
        
        # Construct Reaction Styles
        reaction_styles = {}
        for key in self.vars:
            if key.startswith("style_"):
                anchor = key.replace("style_", "")
                val = self.get_value(key)
                if val and val != "(Auto)":
                    reaction_styles[anchor] = val
        data["reaction_styles"] = reaction_styles

        file_path = self.data_dir / f"{safe_name}.json"
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Success", f"Character saved to:\n{file_path}\n(Assets organized in {char_dir})")
        except Exception as e:
            logger.error(f"Failed to save character: {e}")
            messagebox.showerror("Error", f"Failed to save:\n{e}")

    def load_character(self):
        file_path = filedialog.askopenfilename(initialdir=self.data_dir, title="Select Character JSON", filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Basic Fields
                for key, value in data.items():
                    if key == "example_dialogue":
                        self.set_structured_dialogue_from_text(value)
                    elif key in self.entries:
                        self.set_value(key, value)
                
                # System Params
                sys_p = data.get("system_params", {})
                pm = sys_p.get("pacemaker", {})
                self.set_value("pm_interval", pm.get("base_interval_sec", 60))
                self.set_value("pm_variance", pm.get("variance", 0.2))
                
                vad_b = sys_p.get("vad_baseline", {})
                self.set_value("vad_b_v", vad_b.get("valence", 0.0))
                self.set_value("vad_b_a", vad_b.get("arousal", 0.0))
                self.set_value("vad_b_d", vad_b.get("dominance", 0.0))

                vad_v = sys_p.get("vad_volatility", {})
                self.set_value("vad_v_v", vad_v.get("valence", 1.0))
                self.set_value("vad_v_a", vad_v.get("arousal", 1.0))
                self.set_value("vad_v_d", vad_v.get("dominance", 1.0))
                
                # Reaction Styles
                styles = data.get("reaction_styles", {})
                # Reset all to auto first?
                for key in self.vars:
                    if key.startswith("style_"):
                         self.vars[key].set("(Auto)")
                         
                for anchor, style in styles.items():
                    if f"style_{anchor}" in self.vars:
                        self.set_value(f"style_{anchor}", style)

                messagebox.showinfo("Success", f"Loaded character from:\n{Path(file_path).name}")
            except Exception as e:
                logger.error(f"Failed to load character: {e}")
                messagebox.showerror("Error", f"Failed to load:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = CharacterCreatorWindow(root)
    root.mainloop()
