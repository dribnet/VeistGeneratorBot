from typing import Dict
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from merging.reaction_merger import ReactionMerger
import json

prompt_prefix = """
Below is a text description of an image prompt which needs to be modified and improved.
The modifications are in the form of emoji reactions with counters in json format.

I will provide an example below so you understand the format, but do not the content it influence your actual task:

prompt="A tortise is seen walking through the lonely desert."
reactions={"🌈":10, "⭐":3}

The task is to rewrite the image description creatively interpreting the reactions as possible improvements.
You should not include the reactions directly, but they should influence the conent of the prompt.
The influence should be weigted based on the counters.
So in this example there should be a heavy "rainbow" and light "star" influence.
Possible reactions here could be

A tortise is seen walking beneath a bright rainbow through the lonely desert under the night sky.

or 

A tortise with a bright rainbow colored shell walks through the desert leaving footprints that look like stars.

Your prompt should be descriptive and creative.
Repond only with the prompt itself and then stop. Do not put the prompt in quotes.
Please stick as close as possible only to content of the prompt and reations below.

Here are your prompt and reactions:

"""

class DeepseekMerger(ReactionMerger):
    def __init__(self):
        # self.model_name = "deepseek-ai/DeepSeek-R1-Distill-Llama-8B"
        self.model_name = "Qwen/Qwen2.5-1.5B-Instruct"
        # model_name = "google/gemma-2-2b-it"

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        # model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto", torch_dtype=torch.float)
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name)

    """Simple append strategy that adds 'more X' for each reaction"""
    def merge(self, prompt: str, reactions: Dict[str, int]) -> str:
        print(f"DeepseekMerger received prompt: {prompt}")
        print(f"DeepseekMerger received reactions: {reactions}")
        
        if not reactions:
            print("No reactions, returning original prompt")
            return prompt

        # Filter out reactions with count 0
        active_reactions = {k: v for k, v in reactions.items() if v > 0}
        # print(f"Active reactions after filtering: {active_reactions}")
        
        if not active_reactions:
            print("No active reactions after filtering, returning original prompt")
            return prompt
        
        reactions_string = json.dumps(reactions)
        prompt_suffix = f'prompt="{prompt}"\nreations={reactions_string}\n'
        prompt = prompt_prefix + prompt_suffix

        messages = [
            {"role": "user", "content": prompt},
         ]
        tokenized_chat = self.tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt")
        outputs = self.model.generate(tokenized_chat, max_new_tokens=1024)

        raw_output = self.tokenizer.decode(outputs[0])
        print("raw_outputs: {raw_output}")

        # Deepseek
        output_pair = raw_output.split('</think>')
        result = output_pair[-1].strip()
        result = result.removesuffix('<｜end▁of▁sentence｜>')

        #  Qwen
        output_pair = result.split('<|im_start|>assistant')
        result = output_pair[-1].strip()
        result = result.removesuffix('<|im_end|>')

        print(f"Generated new prompt: {result}")
        return result
