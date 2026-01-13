import json
import re
from typing import Any, Dict, List, Union, Callable
from src.foundation.logging import logger
from src.foundation.types import Result

class JsonRepair:
    """
    Utilities for robustly extracting and parsing JSON from LLM outputs.
    Focuses on SYNTACTIC repair (getting a valid dict/list from string).
    """

    @staticmethod
    def extract_and_parse(text: str) -> Result[Union[Dict, List]]:
        """
        Main entry point. Attempts to extract and parse JSON using multiple strategies.
        """
        if not text:
            return Result.fail("Empty input text")

        cleaned_text = JsonRepair._extract_json_block(text)
        
        # Strategy List
        strategies: List[Callable[[str], Any]] = [
            # 1. Standard Parse
            lambda t: json.loads(t),
            
            # 2. Repair Common Regex Issues (Comments, Trailing Commas)
            lambda t: json.loads(JsonRepair._repair_regex_patterns(t)),
            
            # 3. Truncation Recovery (Try closing brackets)
            lambda t: json.loads(t + "}"),
            lambda t: json.loads(t + "}]}"),
            
            # 4. Aggressive Combination
            lambda t: json.loads(JsonRepair._repair_regex_patterns(t) + "}"),
            
            # 5. Fallback: Python Literal Eval (Dangerous but effective for single quotes)
            lambda t: __import__('ast').literal_eval(t)
        ]

        errors = []
        for strategy in strategies:
            try:
                result = strategy(cleaned_text)
                if isinstance(result, (dict, list)):
                    return Result.ok(result)
            except Exception as e:
                errors.append(str(e))
                continue

        return Result.fail(f"All JSON parse strategies failed. Errors: {errors[:3]}...")

    @staticmethod
    def _extract_json_block(text: str) -> str:
        """Extracts content within ```json ... ``` or finds the outermost {}/[] block."""
        # 1. Markdown Code Block
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # 2. Outermost Brackets (Heuristic)
        start_obj = text.find("{")
        end_obj = text.rfind("}")
        
        start_arr = text.find("[")
        end_arr = text.rfind("]")
        
        # Decide if it looks like an object or array
        candidates = []
        if start_obj != -1 and end_obj > start_obj:
            candidates.append((start_obj, end_obj, text[start_obj : end_obj + 1]))
        if start_arr != -1 and end_arr > start_arr:
            candidates.append((start_arr, end_arr, text[start_arr : end_arr + 1]))
            
        if candidates:
            # Pick the one that starts earliest? Or longest? 
            # Usually LLM output starts with text then JSON.
            candidates.sort(key=lambda x: x[0])
            return candidates[0][2]
            
        return text.strip()

    @staticmethod
    def _repair_regex_patterns(text: str) -> str:
        """Repairs common JSON syntax errors via Regex."""
        # 1. Trailing commas: , } -> }
        text = re.sub(r",(\s*[}\]])", r"\1", text)
        
        # 2. Comments: // ... or /* ... */
        text = re.sub(r"//.*", "", text)
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        
        # 3. Missing comma between objects: } { -> }, {
        text = re.sub(r"(\})\s*(\{)", r"\1, \2", text)
        
        # 4. Unescaped quotes in values (Simple heuristic)
        # It's hard to do perfectly with regex, skipping for now to avoid false positives.
        
        return text
