"""
engine.py
---------
From-scratch Heads-Up Limit Texas Hold'em engine, built to the exact
mechanical spec (blinds, fixed bet sizes, 4-bet cap, HU turn order,
split pots). Used for local testing/simulation of agent.py bots; the
official tournament arena has its own copy of this logic, but this one
matches it so bots can be developed and sanity-checked locally.

Key design note on the "big blind option" and, more generally, when a
betting round closes:

  We track a `players_to_act` set. Both players start each street in
  that set -- including the big blind pre-flop, even though the BB has
  already contributed chips via the forced blind. This single rule
  naturally reproduces the BB option (SB calls -> BB is still in
  players_to_act -> BB gets to check/raise) without any special-casing,
  and generalizes cleanly to every post-flop street (bet/raise resets
  players_to_act to {opponent}; call/check removes the actor from it;
  street ends when the set is empty).
"""

from card import Card, Deck, to_cards
from evaluator import best_hand_score


class HandResult:
    def __init__(self, stack_deltas, folded_player=None, showdown=None):
        self.stack_deltas = stack_deltas      # dict {0: delta, 1: delta}
        self.folded_player = folded_player    # None if it went to showdown
        self.showdown = showdown              # dict with hole cards / board / winner, or None

    def __repr__(self):
        if self.folded_player is not None:
            return f"HandResult(fold by {self.folded_player}, deltas={self.stack_deltas})"
        return f"HandResult(showdown, deltas={self.stack_deltas})"


class HeadsUpLimitEngine:
    STARTING_STACK = 100
    SMALL_BLIND = 1
    BIG_BLIND = 2
    SMALL_BET = 2
    BIG_BET = 4
    MAX_BETS_PER_STREET = 4

    def __init__(self, bot0, bot1, rng=None, verbose=False):
        self.bots = {0: bot0, 1: bot1}
        self.rng = rng
        self.verbose = verbose

    def _log(self, *args):
        if self.verbose:
            print(*args)

    def play_hand(self, dealer):
        """dealer: 0 or 1 -- which seat posts the small blind / acts first pre-flop.
        Returns a HandResult with stack deltas relative to the fresh 100-chip stacks."""
        other = 1 - dealer
        stacks = {dealer: self.STARTING_STACK, other: self.STARTING_STACK}
        pot = 0

        deck = Deck()
        deck.shuffle(self.rng)
        hole = {dealer: deck.draw(2), other: deck.draw(2)}
        community = []

        # Post blinds
        stacks[dealer] -= self.SMALL_BLIND
        stacks[other] -= self.BIG_BLIND
        pot += self.SMALL_BLIND + self.BIG_BLIND
        contributions = {dealer: self.SMALL_BLIND, other: self.BIG_BLIND}

        self._log(f"-- Hand start. Dealer={dealer}. Hole cards: {hole}")

        # Pre-flop (dealer/SB acts first), bet size = SMALL_BET, BB's forced bet counts as bet #1
        pot, stacks, folded = self._betting_round(
            contributions=contributions, pot=pot, stacks=stacks,
            first_actor=dealer, bet_increment=self.SMALL_BET,
            num_bets_placed=1, hole=hole, community=community,
        )
        if folded is not None:
            return self._settle_fold(folded, dealer, other, stacks, pot)

        # Flop
        community += [str(c) for c in deck.draw(3)]
        self._log(f"Flop: {community}")
        pot, stacks, folded = self._betting_round(
            contributions={dealer: 0, other: 0}, pot=pot, stacks=stacks,
            first_actor=other, bet_increment=self.SMALL_BET,
            num_bets_placed=0, hole=hole, community=community,
        )
        if folded is not None:
            return self._settle_fold(folded, dealer, other, stacks, pot)

        # Turn
        community += [str(c) for c in deck.draw(1)]
        self._log(f"Turn: {community}")
        pot, stacks, folded = self._betting_round(
            contributions={dealer: 0, other: 0}, pot=pot, stacks=stacks,
            first_actor=other, bet_increment=self.BIG_BET,
            num_bets_placed=0, hole=hole, community=community,
        )
        if folded is not None:
            return self._settle_fold(folded, dealer, other, stacks, pot)

        # River
        community += [str(c) for c in deck.draw(1)]
        self._log(f"River: {community}")
        pot, stacks, folded = self._betting_round(
            contributions={dealer: 0, other: 0}, pot=pot, stacks=stacks,
            first_actor=other, bet_increment=self.BIG_BET,
            num_bets_placed=0, hole=hole, community=community,
        )
        if folded is not None:
            return self._settle_fold(folded, dealer, other, stacks, pot)

        # Showdown
        return self._settle_showdown(hole, community, dealer, other, stacks, pot)

    def _betting_round(self, contributions, pot, stacks, first_actor,
                        bet_increment, num_bets_placed, hole, community):
        current_bet = max(contributions.values())
        players_to_act = {0, 1}
        actor = first_actor

        while players_to_act:
            opponent = 1 - actor
            amount_to_call = current_bet - contributions[actor]
            amount_to_call = min(amount_to_call, stacks[actor])  # can't owe more than stack

            legal_actions = ["CALL"]
            if amount_to_call > 0:
                legal_actions = ["FOLD", "CALL"]
            if num_bets_placed < self.MAX_BETS_PER_STREET and stacks[actor] > amount_to_call:
                legal_actions.append("RAISE")

            action = self.bots[actor].get_action(
                hole_cards=[str(c) for c in hole[actor]],
                community_cards=list(community),
                pot_size=pot,
                stack_size=stacks[actor],
                amount_to_call=amount_to_call,
                legal_actions=list(legal_actions),
            )

            if action not in legal_actions:
                # Illegal action -> treat as an auto-fold safeguard so a buggy
                # bot can't crash the arena; a real arena would penalize this.
                self._log(f"Player {actor} returned illegal action {action!r}; auto-folding.")
                action = "FOLD"

            self._log(f"Player {actor} acts {action} (to_call={amount_to_call}, pot={pot})")

            if action == "FOLD":
                return pot, stacks, actor

            if action == "CALL":
                stacks[actor] -= amount_to_call
                pot += amount_to_call
                contributions[actor] += amount_to_call
                players_to_act.discard(actor)

            elif action == "RAISE":
                raise_cost = amount_to_call + bet_increment
                raise_cost = min(raise_cost, stacks[actor])
                stacks[actor] -= raise_cost
                pot += raise_cost
                contributions[actor] += raise_cost
                current_bet = contributions[actor]
                num_bets_placed += 1
                players_to_act = {opponent}

            actor = opponent

        return pot, stacks, None

    def _settle_fold(self, folded, dealer, other, stacks, pot):
        winner = 1 - folded
        stacks[winner] += pot
        deltas = {p: stacks[p] - self.STARTING_STACK for p in (dealer, other)}
        return HandResult(deltas, folded_player=folded)

    def _settle_showdown(self, hole, community, dealer, other, stacks, pot):
        score0 = best_hand_score(to_cards(hole[0]) + to_cards(community))
        score1 = best_hand_score(to_cards(hole[1]) + to_cards(community))
        if score0 > score1:
            stacks[0] += pot
        elif score1 > score0:
            stacks[1] += pot
        else:
            stacks[0] += pot // 2
            stacks[1] += pot - pot // 2  # odd chip to player 1 by convention
        deltas = {p: stacks[p] - self.STARTING_STACK for p in (dealer, other)}
        return HandResult(deltas, folded_player=None,
                           showdown={"hole": dict(hole), "community": list(community),
                                     "score0": score0, "score1": score1})
