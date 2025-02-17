import unittest
from generator import VeistGenerator

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
    
    def test_generate_image(self):
        # Test generation when not active
        result = self.generator.generate_image()
        self.assertIn("error", result)
        
        # Test prompter generation
        self.generator.start_prompter()
        result = self.generator.generate_image("test prompt")
        self.assertEqual(result["type"], "prompter")
        self.assertEqual(result["prompt"], "test prompt")
        
        # Test genrec generation
        self.generator.stop()
        self.generator.start_genrec()
        result = self.generator.generate_image()
        self.assertEqual(result["type"], "genrec")

if __name__ == '__main__':
    unittest.main()