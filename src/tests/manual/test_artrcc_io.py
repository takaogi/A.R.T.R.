
import sys
import os
import shutil
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.foundation.types import Result
from src.modules.character.schema import CharacterProfile
from src.modules.character.artrcc_handler import ARTRCCLoader, ARTRCCSaver

def test_artrcc_cycle():
    print("Testing ARTRCC IO Cycle...")
    
    test_dir = Path("test_output")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir()
    
    # 1. Create Dummy Profile & Assets
    asset_file = test_dir / "test_image.png"
    with open(asset_file, "w") as f:
        f.write("dummy image content")
        
    profile = CharacterProfile(name="TestChar", description="A test character.")
    profile.asset_map = {"test_image.png": str(asset_file.absolute())}
    
    export_path = test_dir / "test_char.artrcc"
    
    # 2. Test Save
    print(f"Saving to {export_path}...")
    res_save = ARTRCCSaver.save(profile, export_path)
    if not res_save.success:
        print(f"FAIL: Save failed: {res_save.error}")
        return
    print("PASS: Save success.")
    
    # 3. Test Load
    print(f"Loading from {export_path}...")
    loader = ARTRCCLoader()
    
    # We need to mock PathManager? 
    # ARTRCCLoader uses PathManager.get_instance().get_characters_dir()
    # We should set up a dummy char dir.
    from src.foundation.paths.manager import PathManager
    # Hack: Inject temp dir
    class MockPathManager:
        def get_characters_dir(self):
            return test_dir / "characters_data"
            
    loader.paths = MockPathManager()
    
    res_load = loader.load(export_path, character_name_override="ImportedTestChar")
    if not res_load.success:
         print(f"FAIL: Load failed: {res_load.error}")
         return
         
    data = res_load.data
    p_dict = data['profile_dict']
    
    if p_dict['name'] == "TestChar":
        print("PASS: Profile name matches.")
    else:
        print(f"FAIL: Profile name mismatch: {p_dict['name']}")

    # Check assets
    char_root = Path(data['character_root'])
    extracted_asset = char_root / "assets" / "test_image.png"
    if extracted_asset.exists():
        print("PASS: Asset extracted.")
    else:
        print("FAIL: Asset not found.")
        
    print("Test Complete.")

if __name__ == "__main__":
    test_artrcc_cycle()
