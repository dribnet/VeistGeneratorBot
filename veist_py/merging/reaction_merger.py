from typing import Dict

class ReactionMerger:
    """Base class for reaction merging strategies"""
    def merge(self, prompt: str, reactions: Dict[str, int]) -> str:
        raise NotImplementedError