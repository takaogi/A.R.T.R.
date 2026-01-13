import sys
import os
from pydantic import BaseModel

# Add project root to path
sys.path.append(os.getcwd())

from src.modules.llm_client.utils import JsonRepair, SchemaValidator

class TestSchema(BaseModel):
    name: str
    age: int

def verify_json_repair():
    print("--- Starting JSON Repair Verification ---")
    
    # 1. Test Syntactic Repair
    broken_jsons = [
        ('{"name": "test", "age": 20,}', "Trailing Comma"), 
        ('```json\n{"name": "mk", "age": 10}\n```', "Markdown Block"),
        ('Some text {"name": "text", "age": 5} end text', "Embedded JSON"),
        ('{"name": "comment", "age": 30} // This is comment', "Comment"),
    ]
    
    for raw, case in broken_jsons:
        print(f"\n[Syntax] Testing {case}...")
        res = JsonRepair.extract_and_parse(raw)
        if res.success:
            print(f"[OK] Parsed: {res.data}")
        else:
            print(f"[FAIL] {res.error}")

    # 2. Test Schema Validation
    print("\n[Schema] Testing Validation...")
    valid_data = {"name": "Alice", "age": 25}
    invalid_data = {"name": "Bob", "age": "thirty"} # Int expected, got str
    
    res_valid = SchemaValidator.validate_and_repair(valid_data, TestSchema)
    if res_valid.success:
        print(f"[OK] Valid Data: {res_valid.data}")
    else:
        print(f"[FAIL] Valid Data Rejected: {res_valid.error}")

    res_invalid = SchemaValidator.validate_and_repair(invalid_data, TestSchema)
    if not res_invalid.success:
        print(f"[OK] Caught Validation Error: {res_invalid.error}")
    else:
        print(f"[FAIL] Invalid Data Accepted: {res_invalid.data}")

if __name__ == "__main__":
    verify_json_repair()
