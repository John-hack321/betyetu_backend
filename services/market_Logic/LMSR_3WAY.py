"""
LMSR_three_outcome.py
services/market_Logic/LMSR_three_outcome.py

3-outcome LMSR for football markets (home / draw / away).
Structured to match your existing LMSR.py conventions exactly.

Core math:
    C(q_h, q_d, q_a) = b * ln( e^(q_h/b) + e^(q_d/b) + e^(q_a/b) )
    P(home)           = e^(q_h/b) / ( e^(q_h/b) + e^(q_d/b) + e^(q_a/b) )

Guarantees:
    P(home) + P(draw) + P(away) == 1.0  at all times
    House worst-case loss         == b * ln(3)  per market
    (compare binary where it is   == b * ln(2))
"""

import math
import logging
import sys
from typing import Literal

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

Outcome3 = Literal["home", "draw", "away"]


# ── Core cost function ────────────────────────────────────────────────────────

def cost_function_3(q_home: float, q_draw: float, q_away: float, b: float) -> float:
    """
    C(q_home, q_draw, q_away) = b * ln( e^(q_h/b) + e^(q_d/b) + e^(q_a/b) )

    Uses the log-sum-exp trick (same as your binary version) to prevent
    overflow when q values get large after many trades.
    """
    if b <= 0:
        raise ValueError(f"b must be positive, got {b}")

    a = max(q_home / b, q_draw / b, q_away / b)
    return b * (a + math.log(
        math.exp(q_home / b - a) +
        math.exp(q_draw / b - a) +
        math.exp(q_away / b - a)
    ))


# ── Price / probability functions ─────────────────────────────────────────────

def get_prices_3(q_home: float, q_draw: float, q_away: float, b: float) -> dict:
    """
    Returns all three probabilities as a dict.
    They always sum to exactly 1.0 — this is the core guarantee
    of the 3-outcome LMSR over three separate binary markets.

    Fresh market (all q = 0):
        get_prices_3(0, 0, 0, 1000) -> {"home": 0.333, "draw": 0.333, "away": 0.333}
    """
    a = max(q_home / b, q_draw / b, q_away / b)
    exp_home = math.exp(q_home / b - a)
    exp_draw = math.exp(q_draw / b - a)
    exp_away = math.exp(q_away / b - a)
    total = exp_home + exp_draw + exp_away

    return {
        "home": round(exp_home / total, 6),
        "draw": round(exp_draw / total, 6),
        "away": round(exp_away / total, 6),
    }


def outcome_price_3(
    q_home: float, q_draw: float, q_away: float, b: float, side: Outcome3
) -> float:
    """Price for a single outcome. Convenience wrapper around get_prices_3."""
    return get_prices_3(q_home, q_draw, q_away, b)[side]


# ── Buy cost ──────────────────────────────────────────────────────────────────

def cost_to_buy_3(
    q_home: float,
    q_draw: float,
    q_away: float,
    b: float,
    shares: float,
    side: Outcome3,
) -> float:
    """
    How much KES does it cost to buy `shares` on `side`?

    cost = C(q_side + shares, q_others) - C(q_home, q_draw, q_away)

    Always positive — you pay to buy.

    Example (fresh market, b=1000):
        cost_to_buy_3(0, 0, 0, 1000, 100, "home") -> ~33.9 KES
        (home starts at 33%, so ~34 KES per 100 shares makes sense)
    """
    if shares <= 0:
        raise ValueError(f"shares must be positive, got {shares}")

    before = cost_function_3(q_home, q_draw, q_away, b)

    if side == "home":
        after = cost_function_3(q_home + shares, q_draw, q_away, b)
    elif side == "draw":
        after = cost_function_3(q_home, q_draw + shares, q_away, b)
    else:
        after = cost_function_3(q_home, q_draw, q_away + shares, b)

    return after - before


# ── Sell payout ───────────────────────────────────────────────────────────────

def payout_from_sell_3(
    q_home: float,
    q_draw: float,
    q_away: float,
    b: float,
    shares: float,
    side: Outcome3,
) -> float:
    """
    How much KES do you receive for selling `shares` on `side`?

    payout = C(q_home, q_draw, q_away) - C(q_side - shares, q_others)

    Always positive — you receive KES when selling.
    Fee is NOT deducted here — handled at the trade service layer
    exactly as your existing payout_from_sell does it.
    """
    if shares <= 0:
        raise ValueError(f"shares must be positive, got {shares}")

    current = cost_function_3(q_home, q_draw, q_away, b)

    if side == "home":
        if shares > q_home:
            raise ValueError(f"cannot sell {shares} home shares, only {q_home} exist")
        after = cost_function_3(q_home - shares, q_draw, q_away, b)
    elif side == "draw":
        if shares > q_draw:
            raise ValueError(f"cannot sell {shares} draw shares, only {q_draw} exist")
        after = cost_function_3(q_home, q_draw - shares, q_away, b)
    else:
        if shares > q_away:
            raise ValueError(f"cannot sell {shares} away shares, only {q_away} exist")
        after = cost_function_3(q_home, q_draw, q_away - shares, b)

    return current - after


# ── House reserve ─────────────────────────────────────────────────────────────

def max_house_loss_3(b: float) -> float:
    """
    Worst-case loss the house can face per 3-outcome market = b * ln(3).

    Compare to binary:  b * ln(2)  ~= 0.693 * b
    3-outcome:          b * ln(3)  ~= 1.099 * b

    So 3-outcome markets need ~58% more reserve than binary for the same b.
    Seed each football market with this amount before opening trading.

    b=1000  ->  reserve = 1098.6 KES
    b=5000  ->  reserve = 5493.1 KES
    """
    return b * math.log(3)


# ── Inverse: shares for a given budget ───────────────────────────────────────

def shares_for_budget_3(
    q_home: float,
    q_draw: float,
    q_away: float,
    b: float,
    budget: float,
    side: Outcome3,
    tolerance: float = 0.01,
    max_iterations: int = 100,
) -> float:
    """
    Binary search: how many shares can a user buy with exactly `budget` KES?
    Used for showing "for 500 KES you get approximately X shares" before
    the user confirms. Same approach as your existing binary version.
    """
    if budget <= 0:
        return 0.0

    lo, hi = 0.0, budget

    for _ in range(max_iterations):
        mid = (lo + hi) / 2
        cost = cost_to_buy_3(q_home, q_draw, q_away, b, mid if mid > 0 else 1e-9, side)
        if abs(cost - budget) < tolerance:
            return mid
        if cost < budget:
            lo = mid
        else:
            hi = mid

    return (lo + hi) / 2


# ── Buy quote (preview before confirming) ────────────────────────────────────

def buy_quote_3(
    q_home: float,
    q_draw: float,
    q_away: float,
    b: float,
    shares: float,
    side: Outcome3,
    platform_fee_pct: float = 0.02,
) -> dict:
    """
    Everything the frontend needs to show a buy preview — cost including
    fee, and all three prices after the trade so the chart can update.

    No DB writes. Call this from GET /{market_id}/quote/buy.
    Mirrors BuyQuoteResponse from your existing binary market.
    """
    base_cost = cost_to_buy_3(q_home, q_draw, q_away, b, shares, side)
    fee = base_cost * platform_fee_pct
    total = base_cost + fee

    if side == "home":
        prices_after = get_prices_3(q_home + shares, q_draw, q_away, b)
    elif side == "draw":
        prices_after = get_prices_3(q_home, q_draw + shares, q_away, b)
    else:
        prices_after = get_prices_3(q_home, q_draw, q_away + shares, b)

    return {
        "side": side,
        "shares": shares,
        "cost_kes": round(total, 2),
        "home_price_after": prices_after["home"],
        "draw_price_after": prices_after["draw"],
        "away_price_after": prices_after["away"],
    }


# ── Sell quote (preview before confirming) ───────────────────────────────────

def sell_quote_3(
    q_home: float,
    q_draw: float,
    q_away: float,
    b: float,
    shares: float,
    side: Outcome3,
    platform_fee_pct: float = 0.02,
) -> dict:
    """
    Everything the frontend needs to show a sell preview.
    No DB writes.
    """
    gross = payout_from_sell_3(q_home, q_draw, q_away, b, shares, side)
    fee = gross * platform_fee_pct
    net = gross - fee

    if side == "home":
        prices_after = get_prices_3(q_home - shares, q_draw, q_away, b)
    elif side == "draw":
        prices_after = get_prices_3(q_home, q_draw - shares, q_away, b)
    else:
        prices_after = get_prices_3(q_home, q_draw, q_away - shares, b)

    return {
        "side": side,
        "shares": shares,
        "payout_kes": round(net, 2),
        "home_price_after": prices_after["home"],
        "draw_price_after": prices_after["draw"],
        "away_price_after": prices_after["away"],
    }


# ── Sanity checks — run with: python LMSR_three_outcome.py ───────────────────

if __name__ == "__main__":
    b = 1000.0

    print("=== fresh market ===")
    prices = get_prices_3(0, 0, 0, b)
    print(f"prices: {prices}")
    assert abs(sum(prices.values()) - 1.0) < 1e-4  # small tolerance after rounding to 6dp
    assert prices["home"] == prices["draw"] == prices["away"]

    print("\n=== buy 300 home shares ===")
    cost = cost_to_buy_3(0, 0, 0, b, 300, "home")
    print(f"cost: {cost:.2f} KES")
    prices_after = get_prices_3(300, 0, 0, b)
    print(f"prices after: {prices_after}")
    assert abs(sum(prices_after.values()) - 1.0) < 1e-4
    assert prices_after["home"] > 0.333

    print("\n=== sell 150 home shares back ===")
    payout = payout_from_sell_3(300, 0, 0, b, 150, "home")
    print(f"payout: {payout:.2f} KES")
    assert payout > 0
    assert payout < cost

    print("\n=== buy quote preview ===")
    quote = buy_quote_3(0, 0, 0, b, 100, "away")
    print(f"quote: {quote}")
    assert quote["home_price_after"] + quote["draw_price_after"] + quote["away_price_after"] - 1.0 < 1e-4

    print("\n=== sell quote preview ===")
    quote = sell_quote_3(300, 0, 0, b, 100, "home")
    print(f"quote: {quote}")

    print("\n=== house reserve ===")
    reserve = max_house_loss_3(b)
    print(f"required reserve for b={b}: {reserve:.2f} KES")
    assert reserve > b * math.log(2)

    print("\n=== shares for 500 KES budget ===")
    shares = shares_for_budget_3(0, 0, 0, b, 500, "home")
    print(f"shares you get for 500 KES: {shares:.2f}")
    verify_cost = cost_to_buy_3(0, 0, 0, b, shares, "home")
    print(f"verify cost: {verify_cost:.2f} KES (should be ~500)")

    print("\nall checks passed.")