from typing import Dict
import replicate
import os
from dotenv import load_dotenv
from merging.reaction_merger import ReactionMerger

# Load environment variables
load_dotenv()

# System prompt for guiding the model
prompt_prefix = """You are an AI assistant that helps improve image generation prompts based on emoji reactions.
When users react with emojis to an image, it indicates they want more of what that emoji represents in the next image.

Your task is to enhance the given prompt by incorporating the emoji reactions. The reactions are provided as a dictionary
where keys are emojis and values are the count (how many times that reaction was added).

Here is an example of the format (but do not this specific example influence your actual task):

prompt="A tortise is seen walking through the lonely desert."
reactions={"🌈":10, "⭐":3}

Examples of how this might influence content:
- 🔥 might suggest more intensity, energy, or fire elements
- 🌊 might suggest more water elements or flowing qualities
- 🌈 might suggest more color or vibrancy
- 👻 might suggest more spooky or ethereal qualities

If there are multiple emojis provided, you can use the counts in the dictionary to suggest relative strengths.

The enhanced prompt should not be longer than 200 words. Instead of making it longer, simplify the prompt while keeping the emoji influences.

Please return ONLY the enhanced prompt without any explanations or additional text. The enhanced prompt should build upon
the original while incorporating the essence of the reactions.

Here's the prompt and reactions:
"""

class DeepseekReplicateMerger(ReactionMerger):
    def __init__(self):
        # Check if REPLICATE_API_TOKEN is set
        replicate_token = os.getenv('REPLICATE_API_TOKEN')
        if not replicate_token:
            raise ValueError("REPLICATE_API_TOKEN not set in environment variables")
        
        # Set the token in the environment for the replicate library
        os.environ["REPLICATE_API_TOKEN"] = replicate_token
        
        # "lucataco/deepseek-r1-70b:656b5ca19031ecadf6de648f81c7af84cba66eb7a1328fa863d0282a6fa7da7b",
        # "edoproch/deepseekr1-distilled-llama-8b-ollama:a85b1e086bc2d75020847307d094328be0b0f535ba08500e87489151e41dc17a",

        self.model_id = "deepseek-ai/deepseek-r1"

    def merge(self, prompt: str, reactions: Dict[str, int]) -> str:
        print(f"DeepseekReplicateMerger received prompt: {prompt}")
        print(f"DeepseekReplicateMerger received reactions: {reactions}")
        
        if not reactions:
            print("No reactions, returning original prompt")
            return prompt
            
        # Filter out reactions with count 0
        active_reactions = {k: v for k, v in reactions.items() if v > 0}
        
        if not active_reactions:
            print("No active reactions after filtering, returning original prompt")
            return prompt
        
        # Format the input for the model
        reactions_string = str(active_reactions)
        model_prompt = f'{prompt_prefix}prompt="{prompt}"\nreactions={reactions_string}\n'

        
        try:
            # Call the Replicate API
            input_data = {
                "prompt": model_prompt
            }
            print(f"Sending prompt to replicate: {model_prompt}")
            
            # Collect the full response
            full_response = ""
            for event in replicate.stream(
                self.model_id,
                input=input_data
            ):
                if str(event.event) == 'EventType.OUTPUT':
                    full_response += str(event)
                elif str(event.event) == 'EventType.DONE':
                    pass
                else:
                    print(f"ignored event: {vars(event)}")

            print(f"Received response from replicate: {full_response}")
            
            # Deepseek
            output_pair = full_response.split('</think>')
            result = output_pair[-1].strip()
            
            print(f"Generated new prompt: {result}")
            return result
            
        except Exception as e:
            print(f"Error using Replicate API: {str(e)}")
            # Fallback to simple append strategy if API fails
            reaction_list = []
            for reaction, count in active_reactions.items():
                reaction_list.extend([reaction] * count)
                
            reaction_text = " and ".join(reaction_list)
            result = f"{prompt}, but more {reaction_text}"
            print(f"Fallback prompt: {result}")
            return result 