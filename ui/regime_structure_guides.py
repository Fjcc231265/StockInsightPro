"""Linked structure guides for Market regime framework lessons."""

from __future__ import annotations

from typing import Any

# structure_id -> guide metadata shown under regime-framework lesson sections.
REGIME_STRUCTURE_GUIDES: dict[str, dict[str, Any]] = {
    "long_stock": {
        "name": "Long stock",
        "lesson_id": "stock-vs-call",
        "lesson_section": "Long stock",
        "playbook_id": None,
        "simulator": "Stock P&L simulator",
        "template": None,
        "option_defaults": None,
        "numeric_example": (
            "Stock **$100**, buy **100 shares** → **$10,000** capital. "
            "At **$110**: P&L **+$1,000** (+10%). At **$95**: P&L **−$500** (−5%). "
            "No expiration and no theta."
        ),
        "regime_fit": (
            "Fits **risk-on** when the index trend is up, VIX is stable or falling, and you want "
            "to participate in upside without an expiration clock."
        ),
        "simulator_note": (
            "Open **Stock P&L simulator**, set entry **$100** and exit scenarios (e.g. **$110** vs **$95**). "
            "Compare how much capital you tie up versus an option with the same directional view."
        ),
    },
    "long_call": {
        "name": "Long call",
        "lesson_id": "calls-and-puts",
        "lesson_section": "What a call controls",
        "playbook_id": "bullish-long-call",
        "simulator": "Options P&L simulator",
        "template": None,
        "option_defaults": {
            "option_type": "Call",
            "stock_price": 100.0,
            "strike": 100.0,
            "premium": 4.0,
            "implied_volatility": 28.0,
        },
        "numeric_example": (
            "Stock **$100**, buy **100 call** for **$4** → **$400** max risk per contract. "
            "Expiration break-even **$104**. At **$112** at expiry: intrinsic **$12** → **+$800** gross "
            "(**+200%** on premium). At **$100** flat: lose **$400** (100% of premium)."
        ),
        "regime_fit": (
            "Fits **risk-on** with **low–medium IV** when you expect a directional move before expiration "
            "and want defined risk with less capital than stock."
        ),
        "simulator_note": (
            "Open **Options P&L simulator** with the preset below. Raise spot toward **$112** and compare "
            "P&L vs holding stock — notice theta if price stalls near **$102**."
        ),
    },
    "bull_call_spread": {
        "name": "Bull call spread",
        "lesson_id": "close-spread-winners",
        "lesson_section": "Bull call spreads",
        "playbook_id": "bullish-bull-call-spread",
        "simulator": "Strategy payoff lab",
        "template": "Bull call spread",
        "option_defaults": None,
        "numeric_example": (
            "Stock **$100**: buy **100 call @ $5**, sell **110 call @ $2** → net debit **$3** (**$300**/spread). "
            "Max value **$10** → max profit **$700**. Break-even **$103**. "
            "At **$110+**: near max profit. Below **$103** at expiry: lose part or all of **$300**."
        ),
        "regime_fit": (
            "Fits **risk-on** when you are bullish but IV is not cheap — the short call reduces debit "
            "and caps upside at a realistic target."
        ),
        "simulator_note": (
            "Open **Strategy payoff lab**, template **Bull call spread**. "
            "Slide price to **$110** vs **$101** to see why risk-on breakouts need follow-through past break-even."
        ),
    },
    "covered_call": {
        "name": "Covered call",
        "lesson_id": "covered-call",
        "lesson_section": "Structure",
        "playbook_id": "bullish-covered-call",
        "simulator": "Strategy payoff lab",
        "template": "Covered call",
        "option_defaults": None,
        "numeric_example": (
            "Own **100 shares @ $100** ($10,000), sell **110 call @ $3** → collect **$300**. "
            "If stock stays **≤ $110**: keep premium (and stock). "
            "If assigned at **$110**: ~**$1,300** total gain on shares + premium before fees. "
            "If stock rallies to **$125**: upside capped near **$110**."
        ),
        "regime_fit": (
            "Fits **neutral / mildly bullish** or **risk-on** only when you accept capping upside. "
            "Often better when IV is **elevated** and the chart is range-bound."
        ),
        "simulator_note": (
            "In **Strategy payoff lab**, template **Covered call**. "
            "Compare P&L at **$105** (income) vs **$120** (missed upside) — weak fit for strong risk-on trends."
        ),
    },
    "cash_secured_put": {
        "name": "Cash-secured put",
        "lesson_id": "cash-secured-put",
        "lesson_section": "Structure",
        "playbook_id": "bullish-csp",
        "simulator": "Options P&L simulator",
        "template": None,
        "option_defaults": {
            "option_type": "Put",
            "action": "Sell",
            "stock_price": 100.0,
            "strike": 95.0,
            "premium": 2.0,
            "implied_volatility": 32.0,
        },
        "numeric_example": (
            "Stock **$100**, sell **95 put @ $2** with **$9,500** cash reserved → max obligation buy at **$95**. "
            "If expires OTM: keep **$200** per contract. "
            "If assigned: effective entry **~$93** (**$95 − $2** premium)."
        ),
        "regime_fit": (
            "Fits **neutral** ranges when you want income or a lower entry — not aggressive risk-on chasing breakouts."
        ),
        "simulator_note": (
            "In **Options P&L simulator**, choose **Put / Sell** with strike **$95**. "
            "Model spot at **$98** vs **$90** to see assignment economics."
        ),
    },
    "iron_condor": {
        "name": "Iron condor",
        "lesson_id": "iron-condor",
        "lesson_section": "Structure",
        "playbook_id": "neutral-iron-condor",
        "simulator": "Strategy payoff lab",
        "template": None,
        "option_defaults": None,
        "numeric_example": (
            "Stock **$100**, sell **95/90 put spread** and **105/110 call spread**, collect **$2.50** credit (**$250**). "
            "Max loss often **$250** if price pins an wing (width **$5 − $2.50**). "
            "Profits if stock finishes between short strikes near expiry."
        ),
        "regime_fit": (
            "Fits **neutral + elevated IV** when you expect a range and IV contraction — not a clean risk-on trend."
        ),
        "simulator_note": (
            "Use **Strategy payoff lab** (template **Custom** or start from **Iron butterfly**) to model wings. "
            "Stress spot at **$100 ± 8%** to see range vs gap risk when IV is elevated."
        ),
    },
    "credit_spread": {
        "name": "Bear call spread",
        "lesson_id": "vertical-credit-spreads",
        "lesson_section": "Bear call spread",
        "playbook_id": None,
        "simulator": "Strategy payoff lab",
        "template": None,
        "option_defaults": None,
        "numeric_example": (
            "Stock **$100** in a range: sell **105/110 bear call spread** for **$1.50** (**$150** max gain). "
            "Max loss **$350** (width **$5 − $1.50**). Profits if stock stays below **$105**."
        ),
        "regime_fit": (
            "Fits **neutral + high IV** when you have a clear range and accept defined max loss."
        ),
        "simulator_note": (
            "Build a **bear call spread** in **Strategy payoff lab** (template **Custom**). "
            "Stress-test a **+8%** gap to see why the range thesis must be explicit."
        ),
    },
    "protective_put": {
        "name": "Protective put",
        "lesson_id": "protective-put",
        "lesson_section": "Structure",
        "playbook_id": "hedge-protective-put",
        "simulator": "Strategy payoff lab",
        "template": "Protective put",
        "option_defaults": None,
        "numeric_example": (
            "Own **100 shares @ $100**, buy **95 put @ $3** → insurance cost **$300**. "
            "Below **$95** at expiry, put gains offset stock loss. "
            "At **$85**: stock **−$1,500**, put **~+$1,000** → net **−$500** plus **$300** premium."
        ),
        "regime_fit": (
            "Fits **risk-off** when you already own shares and want a floor — not a directional bullish bet."
        ),
        "simulator_note": (
            "**Strategy payoff lab → Protective put**. Move spot down to **$90** vs flat **$100** "
            "to see insurance cost vs downside reduction."
        ),
    },
    "collar": {
        "name": "Collar",
        "lesson_id": "collar",
        "lesson_section": "Structure",
        "playbook_id": "hedge-collar",
        "simulator": "Strategy payoff lab",
        "template": "Collar",
        "option_defaults": None,
        "numeric_example": (
            "Own **100 @ $100**, buy **95 put @ $3**, sell **110 call @ $2** → net hedge cost **$100**. "
            "Downside cushioned near **$95**; upside capped near **$110**."
        ),
        "regime_fit": (
            "Fits **risk-off** or uncertain markets when you want to keep shares but limit both tail risks."
        ),
        "simulator_note": (
            "**Strategy payoff lab → Collar**. Compare outcomes at **$115** (capped) and **$88** (protected)."
        ),
    },
    "bear_put_spread": {
        "name": "Bear put spread",
        "lesson_id": "calls-and-puts",
        "lesson_section": "What a put controls",
        "playbook_id": "bearish-bear-put-spread",
        "simulator": "Strategy payoff lab",
        "template": "Bear put spread",
        "option_defaults": None,
        "numeric_example": (
            "Stock **$100**: buy **100 put @ $5**, sell **90 put @ $2** → debit **$3** (**$300**). "
            "Max value **$10** → max profit **$700** if stock **≤ $90**. Break-even **~$97**."
        ),
        "regime_fit": (
            "Fits **risk-off** for bearish exposure with defined risk — often cleaner than naked puts after IV spikes."
        ),
        "simulator_note": (
            "**Strategy payoff lab → Bear put spread**. Slide to **$92** vs **$103** to see defined bearish payoff."
        ),
    },
    "long_put": {
        "name": "Long put",
        "lesson_id": "calls-and-puts",
        "lesson_section": "What a put controls",
        "playbook_id": "bearish-long-put",
        "simulator": "Options P&L simulator",
        "template": None,
        "option_defaults": {
            "option_type": "Put",
            "stock_price": 100.0,
            "strike": 100.0,
            "premium": 4.5,
            "implied_volatility": 38.0,
        },
        "numeric_example": (
            "Stock **$100**, buy **100 put @ $4.50** → max loss **$450**/contract. "
            "At **$90** expiry: intrinsic **$10** → **+$550** gross. "
            "If stock stays **$102**: lose premium to theta."
        ),
        "regime_fit": (
            "Fits **risk-off** when you expect downside and IV is not already extreme; size down if VIX just spiked."
        ),
        "simulator_note": (
            "**Options P&L simulator → Put / Buy**. Model spot **$92** with fewer days left to see theta vs delta."
        ),
    },
    "long_straddle": {
        "name": "Long straddle",
        "lesson_id": "straddle-strangle",
        "lesson_section": "Long straddle",
        "playbook_id": "vol-long-straddle",
        "simulator": "Strategy payoff lab",
        "template": "Long straddle",
        "option_defaults": None,
        "numeric_example": (
            "Stock **$100**, buy **100 call @ $4** + **100 put @ $4** → total **$8** (**$800**/straddle). "
            "Needs move beyond **$92** or **$108** at expiry (before fees). "
            "IV crush after the event can hurt even if direction is right."
        ),
        "regime_fit": (
            "Fits **high-vol / event** regimes only when you expect a move **larger** than the implied move."
        ),
        "simulator_note": (
            "**Strategy payoff lab → Long straddle**. Compare **±15%** moves vs flat **$100** to see vega/theta risk."
        ),
    },
}

# (lesson_id, section_heading) -> ordered structure ids
REGIME_SECTION_STRUCTURES: dict[tuple[str, str], list[str]] = {
    ("regime-overview", "Risk-on regime"): ["long_stock", "long_call", "bull_call_spread"],
    ("regime-overview", "Neutral or range-bound regime"): ["covered_call", "cash_secured_put", "iron_condor"],
    ("regime-overview", "Risk-off regime"): ["protective_put", "collar", "bear_put_spread"],
    ("regime-overview", "High-volatility event regime"): ["long_straddle", "iron_condor"],
    ("regime-decision-map", "Risk-on"): ["long_stock", "bull_call_spread", "long_call"],
    ("regime-decision-map", "Neutral + high IV"): ["covered_call", "iron_condor", "credit_spread"],
    ("regime-decision-map", "Risk-off"): ["protective_put", "collar", "bear_put_spread"],
    ("regime-decision-map", "Low IV + catalyst"): ["long_call", "bull_call_spread"],
    ("regime-decision-map", "High IV + uncertain direction"): ["long_straddle", "iron_condor"],
    ("volatility-regimes", "High vs low IV on the stock"): [
        "long_call",
        "iron_condor",
        "covered_call",
        "cash_secured_put",
    ],
    ("iv-classification", "Classification into action"): [
        "long_call",
        "bull_call_spread",
        "iron_condor",
        "covered_call",
    ],
}

LESSON_TITLES: dict[str, str] = {
    "stock-vs-call": "Stock vs long call",
    "calls-and-puts": "Calls and puts",
    "stock-call-spread": "Stock vs call spread",
    "covered-call": "Covered call",
    "cash-secured-put": "Cash-secured put",
    "iron-condor": "Iron condor",
    "vertical-credit-spreads": "Bull put and bear call spreads",
    "protective-put": "Protective put",
    "collar": "Collar",
    "straddle-strangle": "Straddle and strangle",
    "close-spread-winners": "Closing spreads at a profit",
}
