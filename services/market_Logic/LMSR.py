import math
from typing import Literal

import logging
import sys

logger= logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)


"""
LMSR (Logarithmic Market Scoring Rule) Math Service

All pure math here — no database, no FastAPI, just functions.
These are the functions you test first before touching any DB code.

Core formulas:
  C(q_yes, q_no) = b * ln(e^(q_yes/b) + e^(q_no/b))   — the cost function
  P(yes)         = e^(q_yes/b) / (e^(q_yes/b) + e^(q_no/b))  — the price function

The log-sum-exp trick prevents floating point overflow when q values get large.
"""

Side = Literal["yes", "no"]


# Core cost function => calculates the market cost at any point in time based on yes and no values

def cost_function(q_yes: float, q_no: float, b: float) -> float:
    """
    C(q_yes, q_no) = b * ln(e^(q_yes/b) + e^(q_no/b))

    Uses the log-sum-exp trick to prevent overflow:
        max_val = max(q_yes/b, q_no/b)
        result  = b * (max_val + ln(e^(q_yes/b - max_val) + e^(q_no/b - max_val)))

    Why this works: we factor out e^max_val from both exponentials, which keeps
    the values we actually compute in (0, 1] rather than (0, infinity).
    """
    if b <= 0:
        raise ValueError(f"b must be positive, got {b}")

    a = max(q_yes / b, q_no / b)
    return b * (a + math.log(
        math.exp(q_yes / b - a) +
        math.exp(q_no / b - a)
    ))


# Price / probability functions 

def yes_price(q_yes: float, q_no: float, b: float) -> float:
    """
    P(yes) = e^(q_yes/b) / (e^(q_yes/b) + e^(q_no/b))

    Returns a value in (0, 1).  Represents the market's implied probability
    that the outcome will be YES.  Starts at 0.5 when q_yes == q_no.

    Also uses log-sum-exp to stay numerically stable.
    """
    a = max(q_yes / b, q_no / b)
    exp_yes = math.exp(q_yes / b - a)
    exp_no  = math.exp(q_no  / b - a)
    return exp_yes / (exp_yes + exp_no)


# since no prices and yes prices always sum to 1, we can calculate no price as 1 - yes price
def no_price(q_yes: float, q_no: float, b: float) -> float:
    """P(no) = 1 - P(yes). Always sums to 1 with yes_price."""
    return 1.0 - yes_price(q_yes, q_no, b)


# we build this for convenience to get both prices at once
def get_prices(q_yes: float, q_no: float, b: float) -> dict:
    """Convenience — return both prices at once."""
    p_yes = yes_price(q_yes, q_no, b)
    return {"yes": round(p_yes, 6), "no": round(1.0 - p_yes, 6)}


# Buy cost => calaculates the cost to buy shares : works for both no and yes shares

def cost_to_buy(
    q_yes: float,
    q_no: float,
    b: float,
    shares: float,
    side: Side,
) -> float:
    """
    How much KES does it cost to buy `shares` shares on `side`?

    cost = C(q_yes + shares, q_no) - C(q_yes, q_no)   [for YES]
    cost = C(q_yes, q_no + shares) - C(q_yes, q_no)   [for NO]

    The result is always positive (you pay money to buy shares).

    Example:
        b = 1000, q_yes = 0, q_no = 0
        Buying 100 YES shares costs about 50.2 KES
        (The YES price starts at 0.5, so ~50 KES per share makes sense)
    """
    if shares <= 0:
        raise ValueError(f"shares must be positive, got {shares}")

    before = cost_function(q_yes, q_no, b)

    if side == "yes":
        after = cost_function(q_yes + shares, q_no, b)
    else:
        after = cost_function(q_yes, q_no + shares, b)

    return after - before


# Sell payout => calculates the payout from selling shares : works for both no and yes shares

def payout_from_sell(
    q_yes: float,
    q_no: float,
    b: float,
    shares: float,
    side: Side,
) -> float:
    """
    How much KES do you receive for selling `shares` shares back to the market?

    payout = C(q_yes, q_no) - C(q_yes - shares, q_no)   [for YES]
    payout = C(q_yes, q_no) - C(q_yes, q_no - shares)   [for NO]

    The result is always positive (you receive money when selling).

    If the price of YES has risen since you bought:  payout > what you paid  → profit
    If the price of YES has fallen since you bought: payout < what you paid  → loss

    We do NOT deduct a fee here — that's done at the API layer.
    """
    if shares <= 0:
        raise ValueError(f"shares must be positive, got {shares}")

    current = cost_function(q_yes, q_no, b)

    if side == "yes":
        if shares > q_yes:
            raise ValueError(
                f"Cannot sell {shares} YES shares, only {q_yes} exist"
            )
        after = cost_function(q_yes - shares, q_no, b)
    else:
        if shares > q_no:
            raise ValueError(
                f"Cannot sell {shares} NO shares, only {q_no} exist"
            )
        after = cost_function(q_yes, q_no - shares, b)

    return current - after


# Resolution payout 

def resolution_payout_per_share(outcome: Side) -> float:
    """
    At resolution, each share on the winning side pays out 1.0 KES per share.
    Losing shares pay out 0.0.

    In practice you multiply this by the user's share count to get their payout.
    The admin resolves markets manually, so this just encodes the rule clearly.
    """
    # We keep this as a function (not a constant) so it's easy to change later
    # e.g. if you want to add a platform fee at resolution.
    return 1.0  # 1 KES per winning share (scale by share count in your service)


# House risk => calculates the maximum loss that the house can face

def max_house_loss(b: float) -> float:
    """
    The absolute worst case loss the house (platform) can face per market.

    max_loss = b * ln(2)

    This is the amount you need to seed each market with as a reserve.
    If you set b=1000, hold 693 KES in reserve for that market.

    Why b*ln(2)? In the extreme case where all money piles onto one side and
    that side wins, the house's loss converges to this value.  It's a
    mathematical guarantee — the LMSR is designed to have this property.
    """
    return b * math.log(2)


# Inverse: how many shares can I buy for a given budget? 

def shares_for_budget(
    q_yes: float,
    q_no: float,
    b: float,
    budget: float,
    side: Side,
    tolerance: float = 0.01,
    max_iterations: int = 100,
) -> float:
    """
    Binary search: how many shares can a user buy with `budget` KES?

    This is the inverse of cost_to_buy.  Useful for showing the user
    "for 500 KES you get approximately X shares" in the UI.

    We binary-search because there is no closed-form inverse of the cost function.

    tolerance: stop when the estimate is within this many KES of the target
    """
    if budget <= 0:
        return 0.0

    lo, hi = 0.0, budget  # upper bound: you cannot get more shares than you paid KES
    # (since minimum cost per share converges to 0 near the extremes but never goes negative)

    for _ in range(max_iterations):
        mid = (lo + hi) / 2
        cost = cost_to_buy(q_yes, q_no, b, mid if mid > 0 else 1e-9, side)
        if abs(cost - budget) < tolerance:
            return mid
        if cost < budget:
            lo = mid
        else:
            hi = mid

    return (lo + hi) / 2


# Validation helpers => helps in checking and validating the price of b so that it is within the acceptable range

def validate_b(b: float, min_b: float = 100.0, max_b: float = 1_000_000.0) -> None:
    """
    Raise ValueError if b is outside the acceptable range.
    Recommended range for your markets: 1000 – 50000 KES.
    """
    if not (min_b <= b <= max_b):
        raise ValueError(
            f"b={b} is outside the allowed range [{min_b}, {max_b}]"
        )


def validate_shares_in_market(q_yes: float, q_no: float) -> None:
    """Both quantities must be non-negative."""
    if q_yes < 0:
        raise ValueError(f"q_yes cannot be negative, got {q_yes}")
    if q_no < 0:
        raise ValueError(f"q_no cannot be negative, got {q_no}")