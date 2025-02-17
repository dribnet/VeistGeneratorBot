from huggingface_hub import InferenceClient
import os
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class VeistGenerator:
    def __init__(self):
        self.active = False
        self.gen_type = 'none'
        self.gen_interval = 30  # seconds
        self.current_prompt = ""
        
        # Initialize HuggingFace client
        hf_token = os.getenv('HF_TOKEN')
        self.client = InferenceClient(token=hf_token) if hf_token else None
        
        # Default model
        self.model = "stabilityai/stable-diffusion-xl-base-1.0"
    
    def generate_image(self, prompt: str = None) -> dict:
        """Actually generate an image using HuggingFace"""
        if not self.active:
            return {"error": "Generator is not active"}
            
        if not self.client:
            return {"error": "HF_TOKEN not set"}
        
        try:
            # Use the provided prompt or current_prompt
            prompt_text = prompt or self.current_prompt or "a beautiful landscape"
            
            # Generate image using the new task-specific method
            image = self.client.text_to_image(
                prompt_text,
                model=self.model,
            )
            
            # Save to a file (optional)
            output_path = f"output_{hash(prompt_text)}.png"
            image.save(output_path)
            
            return {
                "type": self.gen_type,
                "prompt": prompt_text,
                "status": "generated",
                "path": output_path
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "type": self.gen_type,
                "prompt": prompt_text
            }

    def start_prompter(self):
        """Start the prompter-based generation"""
        if self.active:
            return "Generator is already active"
        self.active = True
        self.gen_type = 'prompter'
        return f"Starting prompter generation at {self.gen_interval} second intervals"
    
    def start_genrec(self):
        """Start the generative_recsys-based generation"""
        if self.active:
            return "Generator is already active"
        self.active = True
        self.gen_type = 'genrec'
        return f"Starting genrec generation at {self.gen_interval} second intervals"
    
    def stop(self):
        """Stop the generator"""
        if not self.active:
            return "Generator is not active"
        self.active = False
        self.gen_type = 'none'
        return "Generator stopped"

if __name__ == "__main__":
    # Command line interface for testing
    generator = VeistGenerator()
    
    while True:
        command = input("\nEnter command (start_prompter/start_genrec/stop/generate/quit): ").strip()
        
        if command == "quit":
            break
        elif command == "start_prompter":
            print(generator.start_prompter())
        elif command == "start_genrec":
            print(generator.start_genrec())
        elif command == "stop":
            print(generator.stop())
        elif command == "generate":
            prompt = input("Enter prompt (or press enter for default): ").strip()
            result = generator.generate_image(prompt if prompt else None)
            print(result)
            if "path" in result:
                print(f"Image saved to: {result['path']}")
        else:
            print("Unknown command")