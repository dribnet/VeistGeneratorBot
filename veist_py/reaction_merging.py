from typing import Dict

class ReactionMerger:
    """Base class for reaction merging strategies"""
    def merge(self, prompt: str, reactions: Dict[str, int]) -> str:
        raise NotImplementedError

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

def create_merger(strategy: str = "append") -> ReactionMerger:
    """Factory function to create the appropriate merger"""
    strategies = {
        "append": AppendMerger,
        # Add more strategies here as needed
    }
    
    if strategy not in strategies:
        raise ValueError(f"Unknown reaction merging strategy: {strategy}")
    
    return strategies[strategy]() 