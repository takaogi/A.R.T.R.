import sys
import os
from typing import List

# Add project root to path
sys.path.append(os.getcwd())

from src.foundation.types import Result

def verify_types():
    print("--- Starting Types Verification ---")

    # 1. Success Case
    res_ok = Result[str].ok("Hello World")
    print(f"Success Case: {res_ok}")
    assert res_ok.success is True
    assert res_ok.data == "Hello World"
    assert res_ok.error is None
    print("[OK] Success case verified.")

    # 2. Failure Case
    res_fail = Result[str].fail("Something went wrong")
    print(f"Failure Case: {res_fail}")
    assert res_fail.success is False
    assert res_fail.data is None
    assert res_fail.error == "Something went wrong"
    print("[OK] Failure case verified.")

    # 3. Unwrap Test
    try:
        val = res_ok.unwrap()
        print(f"Unwrapped: {val}")
    except Exception:
        print("[FAIL] Unwrap failed on success result.")

    try:
        res_fail.unwrap()
        print("[FAIL] Unwrap did not raise exception on failed result.")
    except RuntimeError as e:
        print(f"[OK] Unwrap raised exception as expected: {e}")

    # 4. Complex Type Test
    res_list = Result[List[int]].ok([1, 2, 3])
    print(f"List Case: {res_list.data}")
    
    # 5. Pydantic Serialization
    json_output = res_ok.model_dump_json()
    print(f"JSON Output: {json_output}")

if __name__ == "__main__":
    verify_types()
