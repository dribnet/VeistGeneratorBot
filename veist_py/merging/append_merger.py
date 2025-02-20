from typing import Dict
from merging.reaction_merger import ReactionMerger

class AppendMerger(ReactionMerger):
    """Simple append strategy that adds 'more X' for each reaction"""
    def merge(self, prompt: str, reactions: Dict[str, int]) -> str:
        # print(f"AppendMerger received prompt: {prompt}")
        # print(f"AppendMerger received reactions: {reactions}")
        
        if not reactions:
            print("No reactions, returning original prompt")
            return prompt
            
        # Filter out reactions with count 0
        active_reactions = {k: v for k, v in reactions.items() if v > 0}
        # print(f"Active reactions after filtering: {active_reactions}")
        
        if not active_reactions:
            print("No active reactions after filtering, returning original prompt")
            return prompt
            
        # Create list of reactions, repeating based on count
        reaction_list = []
        for reaction, count in active_reactions.items():
            reaction_list.extend([reaction] * count)
            
        reaction_text = " and ".join(reaction_list)
        result = f"{prompt}, but more {reaction_text}"
        # print(f"Generated new prompt: {result}")
        return result

