"""
evaluator.py
------------
From-scratch 7-card hand evaluator for Texas Hold'em.

Strategy:
  1. Generate every 5-card combination out of the 7 available cards
     (2 hole + up to 5 community) using itertools.combinations.
  2. Score each 5-card combination as a comparable tuple:
        (category_rank, tiebreak_1, tiebreak_2, ...)
     where a larger tuple (standard Python tuple comparison) means a
     stronger hand. This lets us use plain max()/sorting with no custom
     comparator.
  3. Return the max-scoring 5-card hand's tuple as the 7-card hand's value.

Category ranks (higher = better):
  8 Straight Flush | 7 Four of a Kind | 6 Full House | 5 Flush
  4 Straight        | 3 Three of a Kind | 2 Two Pair | 1 One Pair | 0 High Card
"""

from itertools import combinations
from collections import Counter
from card import Card, to_cards


def _straight_high(distinct_values_desc):
    """distinct_values_desc: sorted unique card values, descending.
    Returns the high card of a straight if one exists among them, else None.
    Handles the wheel (A-2-3-4-5, where Ace plays low, straight high = 5)."""
    vals = distinct_values_desc
    # Standard consecutive run of 5
    for i in range(len(vals) - 4):
        window = vals[i:i + 5]
        if window[0] - window[4] == 4:
            return window[0]
    # Wheel: A,5,4,3,2
    wheel = {14, 5, 4, 3, 2}
    if wheel.issubset(set(vals)):
        return 5
    return None


def score_5card_hand(cards):
    """cards: exactly 5 Card objects. Returns a comparable tuple."""
    values = sorted((c.value for c in cards), reverse=True)
    suits = [c.suit for c in cards]
    is_flush = len(set(suits)) == 1

    value_counts = Counter(values)
    # sort groups by (count desc, value desc) -> e.g. full house = [(3, x), (2, y)]
    groups = sorted(value_counts.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    group_values_by_count = [v for v, cnt in groups]  # values ordered by strength grouping
    counts_sorted = [cnt for v, cnt in groups]

    distinct_desc = sorted(set(values), reverse=True)
    straight_high = _straight_high(distinct_desc)

    if is_flush and straight_high is not None:
        return (8, straight_high)

    if counts_sorted[0] == 4:
        quad_val = groups[0][0]
        kicker = max(v for v in values if v != quad_val)
        return (7, quad_val, kicker)

    if counts_sorted[0] == 3 and len(groups) > 1 and counts_sorted[1] >= 2:
        trip_val = groups[0][0]
        pair_val = groups[1][0]
        return (6, trip_val, pair_val)

    if is_flush:
        return (5, *values)

    if straight_high is not None:
        return (4, straight_high)

    if counts_sorted[0] == 3:
        trip_val = groups[0][0]
        kickers = sorted((v for v in values if v != trip_val), reverse=True)
        return (3, trip_val, *kickers)

    if counts_sorted[0] == 2 and len(groups) > 1 and counts_sorted[1] == 2:
        pair_vals = sorted([groups[0][0], groups[1][0]], reverse=True)
        kicker = max(v for v in values if v not in pair_vals)
        return (2, *pair_vals, kicker)

    if counts_sorted[0] == 2:
        pair_val = groups[0][0]
        kickers = sorted((v for v in values if v != pair_val), reverse=True)
        return (1, pair_val, *kickers)

    return (0, *values)


def best_hand_score(seven_cards):
    """seven_cards: list of Card (or raw string codes), length 2-7.
    Returns the best achievable score tuple over all 5-card subsets.
    Works even if fewer than 7 cards are supplied (e.g. pre-flop rollouts
    where only hole cards + partial board exist) as long as >= 5 cards."""
    cards = [c if isinstance(c, Card) else Card(c) for c in seven_cards]
    if len(cards) < 5:
        raise ValueError("Need at least 5 cards to score a hand")
    return max(score_5card_hand(list(combo)) for combo in combinations(cards, 5))


def compare_hands(hole_a, hole_b, community):
    """Returns 1 if a wins, -1 if b wins, 0 if tie. Inputs are raw code lists."""
    score_a = best_hand_score(to_cards(hole_a) + to_cards(community))
    score_b = best_hand_score(to_cards(hole_b) + to_cards(community))
    if score_a > score_b:
        return 1
    if score_b > score_a:
        return -1
    return 0


HAND_CATEGORY_NAMES = {
    8: "Straight Flush", 7: "Four of a Kind", 6: "Full House", 5: "Flush",
    4: "Straight", 3: "Three of a Kind", 2: "Two Pair", 1: "One Pair", 0: "High Card",
}


def describe(score):
    return HAND_CATEGORY_NAMES[score[0]]
