"""
Pressure Transient Analysis (PTA) for DST results.

- bourdet_derivative: dΔp / d(ln Δt) with L-window smoothing (Bourdet 1989)
- horner_time:        (tp + Δt) / Δt for buildup analysis
- compute_pta:        wrapper that splits a DSTResults into drawdown + buildup
                      phases and computes Δp + Bourdet derivative for each
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.simulation_model import DSTResults


def bourdet_derivative(dt: np.ndarray, dp: np.ndarray, L: float = 0.2) -> np.ndarray:
    """
    Bourdet derivative dΔp/d(ln Δt) with L-window smoothing.

    For each interior point i, find left neighbor j where ln(dt[i])-ln(dt[j]) >= L
    and right neighbor k where ln(dt[k])-ln(dt[i]) >= L. The derivative uses a
    weighted-mean of the left and right slopes (per Bourdet, Ayoub & Pirard 1989).

    Args:
        dt: elapsed time since phase start, monotonically increasing, > 0
        dp: pressure change |p - p_ref|, same length as dt
        L:  smoothing window in natural-log units (typical 0.1 - 0.3)

    Returns:
        deriv: dp/d(ln dt), same length as dt; NaN at endpoints where
               the L-window can't be filled on both sides.
    """
    dt = np.asarray(dt, dtype=float)
    dp = np.asarray(dp, dtype=float)
    n = len(dt)
    deriv = np.full(n, np.nan)
    lnt = np.log(dt)

    for i in range(1, n - 1):
        # left neighbor: largest j < i with lnt[i] - lnt[j] >= L
        j = i - 1
        while j > 0 and (lnt[i] - lnt[j]) < L:
            j -= 1
        # right neighbor: smallest k > i with lnt[k] - lnt[i] >= L
        k = i + 1
        while k < n - 1 and (lnt[k] - lnt[i]) < L:
            k += 1

        dl = lnt[i] - lnt[j]
        dr = lnt[k] - lnt[i]
        if dl <= 0 or dr <= 0:
            continue

        slope_l = (dp[i] - dp[j]) / dl
        slope_r = (dp[k] - dp[i]) / dr
        deriv[i] = (slope_l * dr + slope_r * dl) / (dl + dr)

    return deriv


def horner_time(dt: np.ndarray, producing_time_s: float) -> np.ndarray:
    """Horner time (tp + Δt) / Δt for buildup analysis."""
    return (producing_time_s + dt) / dt


def equivalent_time(dt: np.ndarray, producing_time_s: float) -> np.ndarray:
    """
    Agarwal equivalent time for buildup: Δt_e = Δt · tp / (tp + Δt).

    Plotting the buildup Bourdet derivative against Δt_e (instead of Δt)
    linearizes superposition: an infinite-acting radial flow signature shows
    up as a flat plateau at the IARF value, just like drawdown, instead of
    decaying as tp/(tp + Δt).
    """
    return dt * producing_time_s / (producing_time_s + dt)


@dataclass
class PTAPhase:
    """PTA data for one flow phase (drawdown or buildup)."""
    dt: np.ndarray            # elapsed time since phase start, seconds
    dp: np.ndarray            # |p - p_ref|, Pa
    bourdet: np.ndarray       # dΔp/d(ln Δt), Pa
    p_ref: float              # reference pressure (initial for dd, shut-in for bu), Pa


@dataclass
class PTA:
    """PTA analysis split into drawdown and buildup phases."""
    drawdown: PTAPhase
    buildup: PTAPhase
    producing_time_s: float   # drawdown duration, used for Horner time

    @property
    def horner_time_buildup(self) -> np.ndarray:
        return horner_time(self.buildup.dt, self.producing_time_s)


def compute_pta(results: DSTResults, L: float | None = None) -> PTA:
    """
    Split DSTResults into drawdown + buildup, compute Δp and Bourdet derivative
    for each. L defaults to results.config.pta.bourdet_L.
    """
    if L is None:
        L = results.config.pta.bourdet_L

    t = results.time
    p = results.pressure_well
    dd_mask = results.drawdown_mask
    bu_mask = results.buildup_mask

    # --- drawdown ---
    p_init = p[0]                                # ~initial reservoir pressure
    dt_dd  = t[dd_mask]                          # already starts at first step
    dp_dd  = p_init - p[dd_mask]                 # drop magnitude (positive)
    bd_dd  = bourdet_derivative(dt_dd, dp_dd, L=L)

    # --- buildup ---
    t_shutin = t[dd_mask][-1]                    # last drawdown timestamp
    p_shutin = p[dd_mask][-1]                    # BHP at shut-in
    dt_bu = t[bu_mask] - t_shutin                # time since shut-in
    dp_bu = p[bu_mask] - p_shutin                # rise magnitude (positive)
    bd_bu = bourdet_derivative(dt_bu, dp_bu, L=L)

    return PTA(
        drawdown=PTAPhase(dt=dt_dd, dp=dp_dd, bourdet=bd_dd, p_ref=p_init),
        buildup=PTAPhase(dt=dt_bu, dp=dp_bu, bourdet=bd_bu, p_ref=p_shutin),
        producing_time_s=t_shutin,
    )
