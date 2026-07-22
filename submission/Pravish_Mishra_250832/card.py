"""
card.py
-------
Core Card and Deck primitives for the from-scratch HULHE engine.

Cards are represented externally as 2-character strings, e.g. 'Ah', 'Td', '7c'.
Internally we wrap them in a Card object so we get free ordering / equality
via dunder methods (__eq__, __lt__, __gt__, __repr__) instead of hand-rolled
comparison logic scattered through the evaluator and engine.
"""

import random

RANK_ORDER = "23456789TJQKA"          # index position -> numeric strength
RANK_TO_VALUE = {r: i + 2 for i, r in enumerate(RANK_ORDER)}
VALUE_TO_RANK = {v: r for r, v in RANK_TO_VALUE.items()}
SUITS = "shdc"                          # spades, hearts, diamonds, clubs


class Card:
    __slots__ = ("rank", "suit", "value")

    def __init__(self, code):
        """
        code: a 2-character string like 'Ah', 'Td', '2c'.
        Accepts either a raw string or an existing Card (idempotent).
        """
        if isinstance(code, Card):
            self.rank, self.suit, self.value = code.rank, code.suit, code.value
            return
        if len(code) != 2:
            raise ValueError(f"Invalid card code: {code!r}")
        rank, suit = code[0].upper(), code[1].lower()
        if rank not in RANK_TO_VALUE:
            raise ValueError(f"Invalid rank in card code: {code!r}")
        if suit not in SUITS:
            raise ValueError(f"Invalid suit in card code: {code!r}")
        self.rank = rank
        self.suit = suit
        self.value = RANK_TO_VALUE[rank]

    def __repr__(self):
        return f"{self.rank}{self.suit}"

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return self.rank == other.rank and self.suit == other.suit

    def __lt__(self, other):
        return self.value < other.value

    def __le__(self, other):
        return self.value <= other.value

    def __gt__(self, other):
        return self.value > other.value

    def __ge__(self, other):
        return self.value >= other.value

    def __hash__(self):
        return hash((self.rank, self.suit))


class Deck:
    """A standard 52-card deck. Supports removing known cards (for Monte
    Carlo rollouts where hole/board cards are already fixed)."""

    def __init__(self, exclude=None):
        exclude_set = set()
        if exclude:
            exclude_set = {Card(c) for c in exclude}
        self.cards = [
            Card(r + s)
            for r in RANK_ORDER
            for s in SUITS
            if Card(r + s) not in exclude_set
        ]

    def shuffle(self, rng=None):
        (rng or random).shuffle(self.cards)
        return self

    def draw(self, n=1):
        drawn = self.cards[:n]
        self.cards = self.cards[n:]
        return drawn

    def __len__(self):
        return len(self.cards)


def to_cards(codes):
    """Convert a list of raw string codes into Card objects."""
    return [Card(c) for c in codes]
