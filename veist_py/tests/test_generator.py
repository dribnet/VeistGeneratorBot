import unittest
from generator import VeistGenerator
import os
from pathlib import Path

class TestVeistGenerator(unittest.TestCase):
    def setUp(self):
        self.generator = VeistGenerator()
    
    def test_initial_state(self):
        self.assertFalse(self.generator.active)
        self.assertEqual(self.generator.gen_type, 'none')
    
    def test_start_prompter(self):
        result = self.generator.start_prompter()
        self.assertTrue(self.generator.active)
        self.assertEqual(self.generator.gen_type, 'prompter')
        self.assertIn("Starting prompter generation", result)
    
    def test_start_genrec(self):
        result = self.generator.start_genrec()
        self.assertTrue(self.generator.active)
        self.assertEqual(self.generator.gen_type, 'genrec')
        self.assertIn("Starting genrec generation", result)
    
    def test_stop(self):
        self.generator.start_prompter()
        result = self.generator.stop()
        self.assertFalse(self.generator.active)
        self.assertEqual(self.generator.gen_type, 'none')
        self.assertEqual(result, "Generator stopped")
    
    def test_generate_image_without_token(self):
        self.generator.start_prompter()
        if not os.getenv('HF_TOKEN'):
            result = self.generator.generate_image("test prompt")
            self.assertIn("error", result)
            self.assertEqual(result["error"], "HF_TOKEN not set")
    
    @unittest.skipIf(not os.getenv('HF_TOKEN'), "HF_TOKEN not set")
    def test_actual_image_generation(self):
        self.generator.start_prompter()
        result = self.generator.generate_image("a beautiful sunset")
        self.assertEqual(result["status"], "generated")
        output_path = Path(result["path"])
        self.assertTrue(output_path.exists())
        # Clean up
        if output_path.exists():
            output_path.unlink()
    
    @unittest.skipIf(not os.getenv('HF_TOKEN'), "HF_TOKEN not set")
    def test_reaction_system(self):
        self.generator.start_reaction()
        
        # Generate initial image
        result1 = self.generator.generate_image("test image")
        self.assertEqual(result1["status"], "generated")
        
        # Add some reactions
        reaction_result = self.generator.add_reaction(result1["path"], "happy")
        self.assertEqual(reaction_result["status"], "added")
        
        # Generate new image influenced by reactions
        result2 = self.generator.generate_image("test image")
        self.assertIn("Based on reactions", result2["prompt"])
        
        # Clean up
        if "path" in result1:
            Path(result1["path"]).unlink()
        if "path" in result2:
            Path(result2["path"]).unlink()
            
        # Additional assertions to debug
        if "error" in result2:
            print(f"Generation error: {result2['error']}")

if __name__ == '__main__':
    unittest.main()