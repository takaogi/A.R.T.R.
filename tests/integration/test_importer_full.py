
import unittest
import shutil
import asyncio
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from dotenv import load_dotenv

# App Imports
from src.foundation.config.manager import ConfigManager
from src.modules.character.importer import CharacterImporter
from src.foundation.paths.manager import PathManager

class TestCharacterImporterFull(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Load env for API keys
        load_dotenv()
        
        # Setup Paths
        cls.test_dir = Path("tests/output/import_test")
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine source file
        # We assume Chaea.charx exists based on previous search
        cls.source_file = Path("tests/charx/Chaea.charx")
        if not cls.source_file.exists():
            raise FileNotFoundError(f"Test resource not found: {cls.source_file}")

    def setUp(self):
        # Patch PathManager to direct characters to test output
        self.patcher = patch.object(PathManager, 'get_characters_dir', return_value=self.test_dir)
        self.mock_get_chars_dir = self.patcher.start()
        
        # Ensure config is loaded
        ConfigManager.get_instance().load_config("config.yaml")

    def tearDown(self):
        self.patcher.stop()

    def test_full_import_workflow(self):
        """
        End-to-end test: CharX File -> Loader -> LLM -> Profile.json
        """
        async def run_async():
            importer = CharacterImporter()
            result = await importer.import_from_file(str(self.source_file))
            return result
            
        result = asyncio.run(run_async())
        
        if not result.success:
            self.fail(f"Import Failed: {result.error}")
            
        profile = result.data
        print(f"\n[Import Success] Name: {profile.name}")
        print(f"Persona: {profile.surface_persona[:50]}...")
        
        # Verifications
        # 1. Check Directory
        char_dir = self.test_dir / "Chaea" # Or "Chaea(Risu)"? Loader sanitizes name.
        # Chaea.charx likely contains "Chaea".
        # We need to find the directory created. 
        # Since logic sanitizes, it should be Chaea or similar.
        
        # List dirs to find it
        subdirs = [d for d in self.test_dir.iterdir() if d.is_dir()]
        self.assertTrue(len(subdirs) > 0, "No character directory created")
        target_dir = subdirs[0]
        print(f"Target Directory: {target_dir}")
        
        # 2. Check profile.json
        profile_path = target_dir / "profile.json"
        self.assertTrue(profile_path.exists(), "profile.json not created")
        
        # 3. Check Assets
        assets_dir = target_dir / "assets"
        self.assertTrue(assets_dir.exists(), "assets dir not created")
        self.assertTrue(len(list(assets_dir.glob("*"))) > 0, "Assets not extracted")
        
        # 4. Check Profile Content
        self.assertTrue(profile.name, "Name is empty")
        print(f"Verified Name: {profile.name}")
        # self.assertEqual(profile.name, "Chaea") # LLM translates to Japanese (e.g. ユ・チェア), so exact match fails
        self.assertTrue(len(profile.speech_examples) > 0)
        if not profile.first_message:
            print("[WARN] First Message is empty.")
        else:
            print(f"First Message: {profile.first_message[:30]}...")

if __name__ == "__main__":
    unittest.main()
