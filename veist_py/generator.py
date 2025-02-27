from huggingface_hub import InferenceClient
import os
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import torch
from diffusers import FluxPipeline
import replicate
import requests

# Load environment variables
load_dotenv()

class VeistGenerator:
    def __init__(self, backend='huggingface', debug=False):
        self.active = False
        self.gen_type = 'none'
        self.gen_interval = 30  # seconds
        self.current_prompt = ""
        self.backend = backend
        self.debug = debug
        
        # Initialize the appropriate backend
        if backend == 'huggingface':
            hf_token = os.getenv('HF_TOKEN')
            self.client = InferenceClient(token=hf_token) if hf_token else None
            self.model = "stabilityai/stable-diffusion-xl-base-1.0"
        elif backend == 'flux':
            self.pipe = FluxPipeline.from_pretrained(
                "black-forest-labs/FLUX.1-schnell",
                torch_dtype=torch.bfloat16
            )
            if torch.cuda.is_available():
                self.pipe = self.pipe.to("cuda:0")
            self.model = "black-forest-labs/FLUX.1-schnell"
        elif backend == 'replicate_flux_schnell':
            # Check if REPLICATE_API_TOKEN is set
            if not os.getenv('REPLICATE_API_TOKEN'):
                raise ValueError("REPLICATE_API_TOKEN not set in environment variables")
            self.model = "black-forest-labs/flux-schnell"
        else:
            raise ValueError(f"Unknown backend: {backend}")
        
        # Ensure outputs directory exists
        self.output_dir = Path(__file__).parent / "outputs"
        self.output_dir.mkdir(exist_ok=True)
        
        # Add reaction tracking
        self.reactions: Dict[str, List[str]] = {}  # image_path -> list of reactions
        self.last_generated: str = None  # path to last generated image
    
    def add_reaction(self, image_path: str, reaction: str) -> dict:
        """Add a reaction to an image"""
        if not Path(image_path).exists():
            return {"error": "Image not found"}
            
        if image_path not in self.reactions:
            self.reactions[image_path] = []
        
        self.reactions[image_path].append(reaction)
        return {
            "status": "added",
            "reaction": reaction,
            "total_reactions": len(self.reactions[image_path])
        }
    
    def get_reaction_prompt(self) -> str:
        """Convert recent reactions into a prompt enhancement"""
        if not self.last_generated or self.last_generated not in self.reactions:
            return ""
            
        # Get reactions for last image
        recent_reactions = self.reactions[self.last_generated]
        if not recent_reactions:
            return ""
            
        # Convert reactions to prompt
        reaction_text = ", ".join(recent_reactions)
        return f"Based on reactions: {reaction_text}"
    
    def generate_image(self, prompt: str = None) -> dict:
        """Generate image with optional reaction-based enhancement"""
        if not self.active:
            return {"error": "Generator is not active"}
            
        if self.backend == 'huggingface' and not self.client:
            return {"error": "HF_TOKEN not set"}
        
        try:
            # Use the provided prompt or current_prompt
            base_prompt = prompt or self.current_prompt or "a beautiful landscape"
            
            # Add reaction context if in reaction mode
            if self.gen_type == 'reaction':
                reaction_context = self.get_reaction_prompt()
                full_prompt = f"{base_prompt}. {reaction_context}".strip()
            else:
                full_prompt = base_prompt
            
            if self.debug:
                print(f"Generating {self.backend} image with full prompt: {full_prompt}")
            
            # Generate image using the appropriate backend
            if self.backend == 'huggingface':
                image = self.client.text_to_image(
                    full_prompt,
                    model=self.model,
                )
            elif self.backend == 'flux':
                image = self.pipe(
                    full_prompt,
                    width=1344,
                    height=768,
                    guidance_scale=0.0,
                    num_inference_steps=4,
                    max_sequence_length=256,
                ).images[0]
            elif self.backend == 'replicate_flux_schnell':
                # Use replicate API
                input = {
                    "prompt": full_prompt,
                    "aspect_ratio": "16:9",
                    "output_format": "jpg",
                    "disable_safety_checker": True,
                }
                
                output = replicate.run(
                    "black-forest-labs/flux-schnell",
                    input=input
                )
                
                # Replicate returns a generator, get the first item
                image_url = next(iter(output))
                
                # Download the image
                response = requests.get(image_url)
                if response.status_code != 200:
                    raise Exception(f"Failed to download image: {response.status_code}")
                
                # Convert to PIL Image
                image = Image.open(BytesIO(response.content))
            
            # Save to a file in outputs directory with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"output_{timestamp}_{hash(full_prompt)}.jpg"
            image.save(output_path)
            
            # Track this as the last generated image
            self.last_generated = str(output_path)
            
            return {
                "type": self.gen_type,
                "prompt": full_prompt,
                "status": "generated",
                "path": str(output_path)
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "type": self.gen_type,
                "prompt": full_prompt,
                "status": "error"
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
    
    def start_reaction(self):
        """Start the reaction-based generation"""
        if self.active:
            return "Generator is already active"
        self.active = True
        self.gen_type = 'reaction'
        return f"Starting reaction-based generation at {self.gen_interval} second intervals"
    
    def stop(self):
        """Stop the generator"""
        if not self.active:
            return "Generator is not active"
        self.active = False
        self.gen_type = 'none'
        return "Generator stopped"

if __name__ == "__main__":
    # Updated command line interface
    generator = VeistGenerator()
    
    while True:
        command = input("\nEnter command (start_prompter/start_genrec/start_reaction/stop/generate/react/test/quit): ").strip()
        
        if command == "quit":
            break
        elif command == "start_prompter":
            print(generator.start_prompter())
        elif command == "start_genrec":
            print(generator.start_genrec())
        elif command == "start_reaction":
            print(generator.start_reaction())
        elif command == "react":
            if generator.last_generated:
                reaction = input("Enter reaction: ").strip()
                result = generator.add_reaction(generator.last_generated, reaction)
                print(result)
            else:
                print("No image has been generated yet")
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
