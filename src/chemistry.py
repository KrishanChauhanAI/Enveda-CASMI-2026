"""Mass/adduct primitives shared by EDA and retrieval code.

Version 0.1.0 | 2026-11-19 UTC.
"""
from __future__ import annotations

import math
from typing import Any

# Convert singly charged test adduct m/z to neutral mass; return NaN when the adduct is unknown.
def neutral_mass(mz: float, adduct: Any) -> float:
    try:
        observed = float(mz)
    except (TypeError, ValueError):
        return float("nan")
    if not math.isfinite(observed):
        return float("nan")
    text = str(adduct).replace(" ", "").lower()
    # Neutral-mass shifts include the ion mass and any neutral loss/gain in the adduct label.
    shifts = {
        "[m+h]+": 1.007276, "[m+na]+": 22.989218, "[m+k]+": 38.963158,
        "[m+nh4]+": 18.033823, "[m-h2o+h]+": -17.003289,
        "[m-2h2o+h]+": -35.013854, "[m-h]-": -1.007276,
        "[m-h2o-h]-": -19.017841, "[m+ch2o2-h]-": 44.998201,
        "[m+hcoo]-": 44.998201, "[m+formate]-": 44.998201,
        "[m+cl]-": 34.969402,
    }
    shift = shifts.get(text)
    return observed - shift if shift is not None else float("nan")
