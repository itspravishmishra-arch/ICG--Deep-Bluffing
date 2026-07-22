"""
test_match.py
-------------
Local sanity-check harness: runs a batch of hands between CustomPokerBot
and a few baseline opponents, alternating the dealer button each hand
(since stacks reset every hand per the spec), and reports aggregate
chip-delta win rate. This is NOT the arena -- just a dev tool to confirm
the engine + agent don't crash and produce sane results before submission.
"""

import time
from engine import HeadsUpLimitEngine
from agent import CustomPokerBot
from baseline_bots import RandomBot, CallingStationBot, TightAggressiveBot


def run_match(bot_a, bot_b, num_hands=500, verbose=False):
    engine = HeadsUpLimitEngine(bot_a, bot_b, verbose=verbose)
    total_delta_a = 0
    illegal_count = 0
    for i in range(num_hands):
        dealer = i % 2  # alternate button
        result = engine.play_hand(dealer=dealer)
        total_delta_a += result.stack_deltas[0] if dealer == 0 else -result.stack_deltas[1]
        # NOTE: stack_deltas keys are seat indices (dealer/other), not fixed
        # bot identity, so we reconstruct bot_a's (seat 0 bot) delta directly:
    return total_delta_a


def run_match_fixed_seats(bot_a, bot_b, num_hands=500):
    """Cleaner version: bot_a is always engine seat 0, bot_b seat 1,
    dealer button alternates between seat 0 and seat 1."""
    engine = HeadsUpLimitEngine(bot_a, bot_b, verbose=False)
    bot_a_total = 0
    for i in range(num_hands):
        dealer = i % 2
        result = engine.play_hand(dealer=dealer)
        bot_a_total += result.stack_deltas[0]
    return bot_a_total, -bot_a_total


if __name__ == "__main__":
    matchups = [
        ("CustomPokerBot vs RandomBot", CustomPokerBot("hero"), RandomBot("villain")),
        ("CustomPokerBot vs CallingStationBot", CustomPokerBot("hero"), CallingStationBot("villain")),
        ("CustomPokerBot vs TightAggressiveBot", CustomPokerBot("hero"), TightAggressiveBot("villain")),
    ]

    for label, bot_a, bot_b in matchups:
        start = time.time()
        num_hands = 200
        a_total, b_total = run_match_fixed_seats(bot_a, bot_b, num_hands=num_hands)
        elapsed = time.time() - start
        bb_per_100 = (a_total / num_hands) * 100 / HeadsUpLimitEngine.BIG_BLIND
        print(f"{label}: {num_hands} hands in {elapsed:.1f}s "
              f"| hero delta = {a_total:+d} chips ({bb_per_100:+.1f} BB/100)")

    # One verbose hand for a manual eyeball check of the engine flow
    print("\n--- Verbose single-hand trace ---")
    engine = HeadsUpLimitEngine(CustomPokerBot("hero"), RandomBot("villain"), verbose=True)
    result = engine.play_hand(dealer=0)
    print(result)
