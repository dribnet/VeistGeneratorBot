from typing import Dict

from merging.reaction_merger import ReactionMerger
from merging.append_merger import AppendMerger
from merging.deepseek_merger import DeepseekMerger
from merging.deepseek_replicate_merger import DeepseekReplicateMerger

def create_merger(strategy: str = "append") -> ReactionMerger:
    """Factory function to create the appropriate merger"""
    strategies = {
        "append": AppendMerger,
        "deepseek": DeepseekMerger,
        "deepseek_replicate": DeepseekReplicateMerger,
        # Add more strategies here as needed
    }
    
    if strategy not in strategies:
        raise ValueError(f"Unknown reaction merging strategy: {strategy}")
    
    return strategies[strategy]() 