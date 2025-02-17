class VeistGenerator:
    def __init__(self):
        self.active = False
        self.gen_type = 'none'
        self.gen_interval = 30  # seconds
        self.current_prompt = ""
        
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
    
    def generate_image(self, prompt: str = None) -> dict:
        """Mock image generation"""
        if not self.active:
            return {"error": "Generator is not active"}
        
        # Mock different behavior based on gen_type
        if self.gen_type == 'prompter':
            return {
                "type": "prompter",
                "prompt": prompt or self.current_prompt,
                "status": "generated"
            }
        elif self.gen_type == 'genrec':
            return {
                "type": "genrec",
                "status": "generated"
            }
        else:
            return {"error": "Invalid generator type"}

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
        else:
            print("Unknown command")