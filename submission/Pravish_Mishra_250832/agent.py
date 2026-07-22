"""
agent.py
--------
Entry point for the tournament arena.

Strategy archetype: Monte Carlo simulation to estimate win probability
("equity"), then a direct Expected Value calculation to decide the action.
Written as plain, explicit, step-by-step code rather than routed through
extra abstraction layers, so every step of the technique is visible here.

The two techniques, spelled out:

  1. MONTE CARLO SIMULATION (estimate_equity):
     We don't know the opponent's 2 hole cards, or any community cards
     still to be dealt. So instead of computing win probability exactly,
     we repeatedly imagine ("simulate") one random way the hidden cards
     could turn out, check who would win THAT random world, and average
     the result over many simulated worlds. Run enough simulations and
     the average converges to the true win probability (Law of Large
     Numbers).

  2. EXPECTED VALUE (get_action):
     Once we have a win-probability estimate p, we plug it directly into
         EV(call) = p * (amount we'd win) - (1 - p) * (amount we'd lose)
     and use the sign of that number to decide whether calling is
     profitable. This is the exact formula given in the assignment brief.
"""

import random
from evaluator import best_hand_score

RANKS = "23456789TJQKA"
SUITS = "shdc"

NUM_SIMULATIONS = 80     # how many random worlds to simulate per decision
RAISE_THRESHOLD = 0.62   # equity above which we bet/raise for value


def estimate_equity(hole_cards, community_cards, num_simulations=NUM_SIMULATIONS):
    """
    Monte Carlo estimate of our probability of winning the hand.

    hole_cards:       our 2 known cards, e.g. ['Ah', 'Kd']
    community_cards:  the community cards dealt so far, e.g. ['7s','7c','2d']
    """

    # STEP 1: Build the list of 52 cards, then remove every card we can
    # already see (our hole cards + the community cards on the table).
    # Whatever cards remain are the ones that could plausibly be the
    # opponent's hole cards or the rest of the community cards.
    known_cards = set(hole_cards) | set(community_cards)
    remaining_deck = []
    for rank in RANKS:
        for suit in SUITS:
            card = rank + suit
            if card not in known_cards:
                remaining_deck.append(card)

    # STEP 2: Work out how many more community cards still need to be
    # dealt before the hand reaches showdown (river = 5 community cards).
    num_cards_left_to_deal = 5 - len(community_cards)

    # STEP 3: Run the simulations, one random "possible future" at a time.
    num_wins = 0
    num_ties = 0
    num_losses = 0

    for _ in range(num_simulations):
        # Randomly guess the opponent's hole cards AND the rest of the
        # board, all in one draw from the same shrunken deck, so we never
        # accidentally deal the same card twice.
        random_draw = random.sample(remaining_deck, 2 + num_cards_left_to_deal)
        simulated_opponent_hole = random_draw[0:2]
        simulated_remaining_board = random_draw[2:2 + num_cards_left_to_deal]
        simulated_full_board = community_cards + simulated_remaining_board

        # Score both hands as if the hand had played out this way.
        my_hand_score = best_hand_score(hole_cards + simulated_full_board)
        opponent_hand_score = best_hand_score(simulated_opponent_hole + simulated_full_board)

        if my_hand_score > opponent_hand_score:
            num_wins += 1
        elif my_hand_score == opponent_hand_score:
            num_ties += 1
        else:
            num_losses += 1

    # STEP 4: Equity = win rate, counting a tie as half a win.
    equity = (num_wins + 0.5 * num_ties) / num_simulations
    return equity


def _safe_fallback_action(amount_to_call, legal_actions):
    """
    Last-resort decision used only if something above throws an unexpected
    exception (e.g. a peer bot's engine integration passes a malformed
    value we didn't anticipate). Never raises, and always returns something
    from legal_actions, so a single bad input can cost us one hand's worth
    of equity at worst -- never a tournament-ending crash.
    """
    if amount_to_call == 0 and "CALL" in legal_actions:
        return "CALL"          # free to see the next card, take it
    if "FOLD" in legal_actions:
        return "FOLD"          # don't put more chips at risk under uncertainty
    if "CALL" in legal_actions:
        return "CALL"
    return legal_actions[0]    # absolute last resort


class BasePokerBot:
    def __init__(self, name):
        self.name = name

    def get_action(self, hole_cards, community_cards, pot_size, stack_size,
                   amount_to_call, legal_actions):
        raise NotImplementedError("Your bot logic goes here!")


class CustomPokerBot(BasePokerBot):
    def get_action(self, hole_cards, community_cards, pot_size, stack_size,
                   amount_to_call, legal_actions):
        try:
            # Run the Monte Carlo simulation to get our win-probability estimate.
            equity = estimate_equity(hole_cards, community_cards)

            # --- Direct Expected Value calculation ---
            # If we call, there are two possible outcomes:
            #   - We win the hand: we gain (pot_size + amount_to_call)
            #     (the pot that was already there, plus getting our own call back)
            #   - We lose the hand: we lose the amount_to_call we put in
            # So:
            #     EV(call) = P(win) * (pot_size + amount_to_call)
            #                - P(lose) * amount_to_call
            amount_we_win_if_we_win = pot_size + amount_to_call
            amount_we_lose_if_we_lose = amount_to_call
            probability_of_losing = 1 - equity

            ev_of_calling = (equity * amount_we_win_if_we_win) \
                - (probability_of_losing * amount_we_lose_if_we_lose)

            # --- Decision logic, using that EV number directly ---

            # If calling has negative expected value, folding is better
            # (folding always has EV = 0: we lose nothing more).
            if amount_to_call > 0 and ev_of_calling < 0 and "FOLD" in legal_actions:
                return "FOLD"

            # If our win probability is comfortably ahead of a coin flip,
            # raise for value (grows the pot while we're likely ahead).
            if equity > RAISE_THRESHOLD and "RAISE" in legal_actions:
                return "RAISE"

            # Otherwise, calling (or checking, when amount_to_call is 0) is our move.
            if "CALL" in legal_actions:
                return "CALL"

            # Should be unreachable given the engine's legal_actions construction,
            # but guarantees we never return an invalid action.
            return legal_actions[0]

        except Exception:
            # Tournament-stability net: 10,000 hands against bots we've never
            # seen means inputs we didn't test for are inevitable somewhere.
            # Never let that turn into a crash / forfeited match.
            return _safe_fallback_action(amount_to_call, legal_actions)
