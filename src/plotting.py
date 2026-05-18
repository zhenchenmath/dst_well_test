"""
PTA plotting helpers (Plotly).

Matplotlib's savefig is broken on this Windows machine (DLL crash, exit
-1066598273), so all figures use Plotly. Plotly figures render interactively
in Jupyter and export to standalone HTML via fig.write_html(...).

- plot_loglog_diagnostic: Δp + Bourdet derivative vs Δt on log-log axes
                          (plateau height ≡ kh)
- plot_horner:            buildup BHP vs Horner time (semi-log; slope ≡ kh)
- plot_bhp:               raw BHP vs time (sanity check)
- plot_loglog_overlay:    overlay multiple runs (kh / volume sensitivity)
- plot_horner_overlay:    overlay multiple runs on Horner plot
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from src.pta_analysis import compute_pta
from src.simulation_model import DSTResults

BAR = 1e5    # Pa per bar
HR  = 3600.0


def plot_loglog_diagnostic(results: DSTResults, phase: str = "buildup",
                            fig: go.Figure | None = None,
                            label: str | None = None) -> go.Figure:
    """Log-log Δp + Bourdet derivative vs Δt. phase: 'drawdown' or 'buildup'."""
    pta = compute_pta(results)
    p = pta.buildup if phase == "buildup" else pta.drawdown
    if fig is None:
        fig = go.Figure()
    name = label or results.config.experiment.run

    valid = ~np.isnan(p.bourdet) & (p.dp > 0) & (p.bourdet > 0)
    x = p.dt[valid] / HR
    fig.add_trace(go.Scatter(x=x, y=p.dp[valid] / BAR,
                             mode="lines+markers", name=f"{name} Δp",
                             legendgroup=name))
    fig.add_trace(go.Scatter(x=x, y=p.bourdet[valid] / BAR,
                             mode="lines+markers",
                             marker_symbol="square", line=dict(dash="dash"),
                             name=f"{name} deriv", legendgroup=name))

    fig.update_layout(
        title=f"Log-log diagnostic — {phase}",
        xaxis=dict(title=f"Δt since {phase} start (h)", type="log"),
        yaxis=dict(title="Δp, dΔp/d(ln Δt) (bar)", type="log"),
        width=750, height=520,
    )
    return fig


def plot_horner(results: DSTResults,
                 fig: go.Figure | None = None,
                 label: str | None = None) -> go.Figure:
    """Buildup BHP vs Horner time. Slope on semi-log ≡ qBμ/(4π kh ln10)."""
    pta = compute_pta(results)
    if fig is None:
        fig = go.Figure()
    ht  = pta.horner_time_buildup
    pws = results.pressure_well[results.buildup_mask] / BAR
    fig.add_trace(go.Scatter(x=ht, y=pws, mode="lines+markers",
                             name=label or results.config.experiment.run))
    fig.update_layout(
        title="Horner plot",
        xaxis=dict(title="Horner time (tp + Δt) / Δt",
                   type="log", autorange="reversed"),
        yaxis=dict(title="BHP (bar)"),
        width=750, height=520,
    )
    return fig


def plot_bhp(results: DSTResults,
              fig: go.Figure | None = None,
              label: str | None = None) -> go.Figure:
    """Raw BHP vs time, with shut-in marker."""
    if fig is None:
        fig = go.Figure()
    name = label or results.config.experiment.run
    t_hr  = results.time / HR
    p_bar = results.pressure_well / BAR
    fig.add_trace(go.Scatter(x=t_hr, y=p_bar, mode="lines+markers", name=name))

    t_shutin = results.time[results.drawdown_mask][-1] / HR
    fig.add_vline(x=t_shutin, line=dict(dash="dot", color="grey"),
                  annotation_text="shut-in", annotation_position="top right")
    fig.update_layout(
        title="Bottom-hole pressure",
        xaxis_title="Time (h)", yaxis_title="BHP (bar)",
        width=800, height=420,
    )
    return fig


def plot_loglog_overlay(experiment: dict[str, DSTResults],
                         phase: str = "buildup") -> go.Figure:
    """Overlay log-log diagnostic for all runs in an experiment."""
    fig = go.Figure()
    for name, r in experiment.items():
        plot_loglog_diagnostic(r, phase=phase, fig=fig, label=name)
    fig.update_layout(title=f"Log-log overlay — {phase}  ({len(experiment)} runs)")
    return fig


def plot_horner_overlay(experiment: dict[str, DSTResults]) -> go.Figure:
    """Overlay Horner plots for all runs in an experiment."""
    fig = go.Figure()
    for name, r in experiment.items():
        plot_horner(r, fig=fig, label=name)
    fig.update_layout(title=f"Horner overlay  ({len(experiment)} runs)")
    return fig
