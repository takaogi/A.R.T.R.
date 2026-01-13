
import unittest
import asyncio
import os
import json
from dotenv import load_dotenv
from src.modules.llm_client.client import LLMClient
from src.modules.llm_client.prompts.character_convert.builder import CharacterConvertBuilder
from src.modules.llm_client.prompts.character_convert.schema import GeneratedProfile
from src.foundation.config.schema import LLMProfile, LLMCapabilities, LLMParameter

# Load env immediately
load_dotenv()

class TestCharacterImporter(unittest.TestCase):
    """
    Integration tests for Character Importer Pipeline.
    WARNING: These tests make actual API calls to OpenRouter/LLM Providers.
    """

    def setUp(self):
        # Setup mock client and real dependencies
        self.builder = CharacterConvertBuilder()
        self.client = LLMClient()
        
        # Sample Raw Data (Shortened for testing)
        self.raw_data = {
            "name": "Erika",
            "description": "A quiet librarian who loves ancient books. She wears glasses and a cardigan.",
            "personality": "Shy, Introverted, Intellectual. Secretly writes fantasy novels.",
            "first_mes": "Um... are you looking for a specific book? Please keep your voice down.",
            "mes_example": "<START>\nHi\n<END>\n<START>\nSsh!\n<END>",
            "scenario": "The city library at dusk."
        }
        
        # Determine active profile (We'll use a cheap capable model for testing)
        self.test_profile = LLMProfile(
            provider="openrouter",
            model_name="inflatebot/mn-mag-mell-r1", # Use cheap model for tests
            capabilities=LLMCapabilities(
                supports_structured_outputs=True,
                force_schema_prompt_injection=False
            ),
            parameters=LLMParameter(temperature=0.1)
        )

    def test_prompt_structure_user_system_split(self):
        """Verify prompt is correctly split into System and User messages"""
        messages = self.builder.build_messages(
            data={"raw_data": self.raw_data}, 
            profile=self.test_profile
        )
        
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        
        # Verify System Content contains rules
        self.assertIn("Conversion Rules", messages[0]["content"])
        self.assertIn("Output Language", messages[0]["content"])
        
        # Verify User Content contains raw data
        self.assertIn("# Raw Character Data (Source)", messages[1]["content"])
        self.assertIn("Erika", messages[1]["content"])
        self.assertIn("Please convert and optimize", messages[1]["content"])

    def test_schema_injection_logic(self):
        """Verify schema text injection logic based on capabilities"""
        
        # Case 1: Structured Outputs = True, Forced = False -> NO Injection
        prof_native = self.test_profile.model_copy(deep=True)
        prof_native.capabilities.supports_structured_outputs = True
        prof_native.capabilities.force_schema_prompt_injection = False
        
        msgs_native = self.builder.build_messages({"raw_data": self.raw_data}, prof_native)
        self.assertNotIn("JSON Output Schema (Strict Adherence)", msgs_native[0]["content"])
        
        # Case 2: Structured Outputs = False -> REQUIRED Injection
        prof_legacy = self.test_profile.model_copy(deep=True)
        prof_legacy.capabilities.supports_structured_outputs = False
        
        msgs_legacy = self.builder.build_messages({"raw_data": self.raw_data}, prof_legacy)
        self.assertIn("JSON Output Schema (Strict Adherence)", msgs_legacy[0]["content"])
        
        # Case 3: Structured Outputs = True, Forced = True -> FORCED Injection
        prof_forced = self.test_profile.model_copy(deep=True)
        prof_forced.capabilities.supports_structured_outputs = True
        prof_forced.capabilities.force_schema_prompt_injection = True
        
        msgs_forced = self.builder.build_messages({"raw_data": self.raw_data}, prof_forced)
        self.assertIn("JSON Output Schema (Strict Adherence)", msgs_forced[0]["content"])

    def test_live_importer_execution(self):
        """
        Executes actual API call to verify end-to-end pipeline.
        This tests: Builder -> Router -> LLMClient -> Provider -> API -> Response -> Pydantic Validation
        """
        if not os.getenv("OPENROUTER_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            self.skipTest("No API Key found. Skipping live test.")
        
        print("\n--- Starting Live LLM Execution Test (Character Importer) ---")
        
        # Execute asynchronously
        result = asyncio.run(self.client.execute(
            prompt_name="test_conversion",
            data={"raw_data": self.raw_data},
            override_profile=self.test_profile,
            override_builder=self.builder
        ))
        
        if result.error:
            print(f"Error: {result.error}")
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.data)
        
        # Parse JSON content
        content_str = result.data.content
        print(f"Raw Output: {content_str[:100]}...")
        
        try:
            profile = GeneratedProfile.model_validate_json(content_str)
        except Exception as e:
            self.fail(f"Failed to parse LLM output into GeneratedProfile: {e}")
            
        print("\n--- Generated Profile ---")
        print(f"Name: {profile.name}")
        print(f"Surface Persona: {profile.surface_persona[:50]}...")
        print(f"Inner Persona: {profile.inner_persona[:50]}...")
        
        # Validations
        self.assertTrue(len(profile.name) > 0)
        self.assertTrue(len(profile.surface_persona) > 0)
        
        # Check optional fields handled correctly (source had first_mes, so should exist)
        if profile.first_message:
             print(f"First Message: {profile.first_message[:50]}...")
        
        print("-------------------------------------------------------------")

if __name__ == '__main__':
    unittest.main()
