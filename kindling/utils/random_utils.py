"""Random utilities for deterministic generation."""

import random
import uuid
from typing import Any, Dict, List, Optional, TypeVar

T = TypeVar('T')


class SeededRandom:
    """Seeded random generator for deterministic output."""

    def __init__(self, seed: Optional[int] = None):
        """Initialize with optional seed.

        Args:
            seed: Random seed for deterministic generation
        """
        self.seed = seed
        self.rng = random.Random(seed)

    def randint(self, a: int, b: int) -> int:
        """Generate random integer between a and b inclusive."""
        return self.rng.randint(a, b)

    def uniform(self, a: float, b: float) -> float:
        """Generate random float between a and b."""
        return self.rng.uniform(a, b)

    def choice(self, seq: List[T]) -> T:
        """Choose random element from sequence."""
        return self.rng.choice(seq)

    def choices(self, seq: List[T], k: int) -> List[T]:
        """Choose k random elements with replacement."""
        return self.rng.choices(seq, k=k)

    def sample(self, seq: List[T], k: int) -> List[T]:
        """Choose k random elements without replacement."""
        return self.rng.sample(seq, k)

    def shuffle(self, seq: List[T]) -> None:
        """Shuffle list in place."""
        self.rng.shuffle(seq)

    def weighted_choice(self, weights: Dict[T, float]) -> T:
        """Choose element based on weights.

        Args:
            weights: Dictionary mapping choices to weights

        Returns:
            Chosen element
        """
        choices = list(weights.keys())
        weights_list = list(weights.values())
        return self.rng.choices(choices, weights=weights_list)[0]

    def uuid(self) -> str:
        """Generate deterministic UUID."""
        # Use random bytes for deterministic UUID
        bytes_data = bytes([self.rng.randint(0, 255) for _ in range(16)])
        return str(uuid.UUID(bytes=bytes_data))

    def boolean(self, probability: float = 0.5) -> bool:
        """Generate random boolean with given probability of True."""
        return self.rng.random() < probability