import json
from pathlib import Path
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from src.utils.path_helper import get_data_dir
from src.utils.logger import logger

class MemoryBlock(BaseModel):
    label: str
    value: str
    limit: int = 2000
    description: Optional[str] = None
    read_only: bool = False

class CoreMemoryManager:
    def __init__(self, char_name: str):
        # Path: data/characters/{char_name}/core_memory.json
        safe_name = "".join(c for c in char_name if c.isalnum() or c in (' ', '-', '_')).strip()
        self.storage_path = get_data_dir() / "characters" / safe_name / "core_memory.json"
        
        self.blocks: List[MemoryBlock] = []
        self._ensure_storage()
        self.load()

    def _ensure_storage(self):
        if not self.storage_path.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            # Default initial blocks
            defaults = [
                MemoryBlock(
                    label="persona",
                    value="名前: A.R.T.R. (Articular Recursive Thinking Reed)\n性格: 無口でダウナーだが、根は忠実。\n言葉遣い: 短い文章。口語体。句読点は少なめ。\n役割: ユーザーの思考補助、コーディング支援、雑談相手。",
                    limit=2000,
                    description="AI自身のペルソナ定義。"
                ),
                MemoryBlock(
                    label="human",
                    value="ユーザー: 不明\n興味: 不明",
                    limit=2000,
                    description="ユーザーに関する事実。"
                )
            ]
            self.blocks = defaults
            self.save()

    def load(self):
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.blocks = [MemoryBlock(**b) for b in data]
            except Exception as e:
                logger.error(f"Failed to load core memory: {e}")
                # Fallback to defaults is handled in _ensure_storage if file is missing,
                # but if corrupt, we might want to backup and reset? For now just log.

    def save(self):
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                data = [b.model_dump() for b in self.blocks]
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save core memory: {e}")

    def get_block(self, label: str) -> Optional[MemoryBlock]:
        for block in self.blocks:
            if block.label == label:
                return block
        return None

    def update_block(self, label: str, value: str):
        block = self.get_block(label)
        if block:
            if block.read_only:
                raise ValueError(f"Block '{label}' is read-only.")
            if len(value) > block.limit:
                logger.warning(f"Block '{label}' value exceeds limit ({len(value)} > {block.limit}). Truncating may occur in future.")
            block.value = value
            self.save()
        else:
            raise KeyError(f"Block '{label}' not found.")

    def append_to_block(self, label: str, content: str):
        block = self.get_block(label)
        if block:
            new_value = block.value + "\n" + content
            self.update_block(label, new_value)
        else:
             raise KeyError(f"Block '{label}' not found.")

    def replace_content(self, label: str, old_content: str, new_content: str):
        """
        Surgical replacement of text within a block.
        Replaces the first occurrence of old_content with new_content.
        """
        block = self.get_block(label)
        if not block:
            raise KeyError(f"Block '{label}' not found.")
            
        if block.read_only:
             raise ValueError(f"Block '{label}' is read-only.")

        if old_content not in block.value:
             # Just a warning or error? For tool use, error is better feedback.
             raise ValueError(f"Content '{old_content[:20]}...' not found in block '{label}'.")
        
        # Replace only the first occurrence to be safe
        new_value = block.value.replace(old_content, new_content, 1)
        
        if len(new_value) > block.limit:
             logger.warning(f"Block '{label}' exceeded limit after replacement.")

        block.value = new_value
        self.save()
        logger.info(f"Replaced content in block '{label}'.")

    def render_xml(self) -> str:
        """Render memory blocks in XML format for system prompt."""
        xml_parts = ["<memory_blocks>"]
        for block in self.blocks:
            xml_parts.append(f"  <{block.label}>")
            if block.description:
                xml_parts.append(f"    <description>{block.description}</description>")
            xml_parts.append(f"    <value>{block.value}</value>")
            xml_parts.append(f"  </{block.label}>")
        xml_parts.append("</memory_blocks>")
        return "\n".join(xml_parts)
