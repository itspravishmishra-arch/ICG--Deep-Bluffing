"""
baseline_bots.py
----------------
Simple opponents for local testing against agent.CustomPokerBot.
Not part of the arena submission -- just dev/test scaffolding.
"""

import random
from agent import BasePokerBot


class RandomBot(BasePokerBot):
    """Picks uniformly at random among legal actions."""
    def get_action(self, hole_cards, community_cards, pot_size, stack_size,
                   amount_to_call, legal_actions):
        return random.choice(legal_actions)


class CallingStationBot(BasePokerBot):
    """Never folds, never raises -- calls/checks everything."""
    def get_action(self, hole_cards, community_cards, pot_size, stack_size,
                   amount_to_call, legal_actions):
        return "CALL"


class AlwaysRaiseBot(BasePokerBot):
    """Maximally aggressive -- raises every time it's legal, otherwise calls.
    Stress-tests our engine's 4-bet cap and our bot's fold discipline
    against a hyper-aggressive peer."""
    def get_action(self, hole_cards, community_cards, pot_size, stack_size,
                   amount_to_call, legal_actions):
        if "RAISE" in legal_actions:
            return "RAISE"
        return "CALL"


class AlwaysFoldBot(BasePokerBot):
    """Folds any time it's allowed to, otherwise checks. Degenerate but
    useful for confirming our engine correctly ends hands early and
    settles pots on a fold without any showdown-path bugs."""
    def get_action(self, hole_cards, community_cards, pot_size, stack_size,
                   amount_to_call, legal_actions):
        if "FOLD" in legal_actions:
            return "FOLD"
        return "CALL"


class MonteCarloMirrorBot(BasePokerBot):
    """A second copy of the same Monte Carlo / EV approach, used to check
    that CustomPokerBot doesn't have a hidden first-mover or seat-index
    advantage when playing a mirror of itself -- results should hover
    near 0 BB/100 either direction, since both seats use an identical
    policy and only the alternating dealer button and card randomness
    differ."""
    def get_action(self, hole_cards, community_cards, pot_size, stack_size,
                   amount_to_call, legal_actions):
        from agent import CustomPokerBot as _CPB
        return _CPB(self.name).get_action(hole_cards, community_cards, pot_size,
                                           stack_size, amount_to_call, legal_actions)
class TightAggressiveBot(BasePokerBot):
    """Naive threshold bot with no rollouts -- just checks pair-or-better
    on the known cards it can already see, to give CustomPokerBot a
    somewhat competent opponent to test against besides pure randomness."""
    def get_action(self, hole_cards, community_cards, pot_size, stack_size,
                   amount_to_call, legal_actions):
        from evaluator import best_hand_score
        from card import to_cards
        cards = to_cards(hole_cards) + to_cards(community_cards)
        if len(cards) >= 5:
            score = best_hand_score(cards)
            strong = score[0] >= 1  # pair or better
        else:
            # preflop: crude strength check -- pair, or both cards >= Jack
            r0, r1 = hole_cards[0][0], hole_cards[1][0]
            strong = (r0 == r1) or (r0 in "AKQJ" and r1 in "AKQJ")

        if amount_to_call > 0 and not strong:
            return "FOLD" if "FOLD" in legal_actions else "CALL"
        if strong and "RAISE" in legal_actions:
            return "RAISE"
        return "CALL"
