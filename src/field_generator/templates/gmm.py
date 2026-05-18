import numpy as np
from scipy.stats import norm

from ._spectral import gaussian_correlated_field

MD_TO_M2 = 9.869233e-16  # 1 mD = 9.869233e-16 m²


def generate(
    nx: int,
    ny: int,
    nz: int,
    facies: list[dict],
    poro_std: float = 0.03,
    correlation_length: float = 0.25,
    seed: int | None = None,
    **_,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Facies-based perm/poro field using Truncated Gaussian Simulation (TGS).

    Models geology as discrete units (facies) — e.g., shale / siltstone / sandstone —
    each with its own permeability distribution. A single spatially-correlated Gaussian
    indicator field is thresholded into facies zones according to the specified weights,
    giving spatially connected geological bodies. Each cell then draws from its facies's
    log-normal permeability distribution.

    Args:
        facies: list of facies dicts, ordered low-to-high perm, each containing:
            weight:       volume fraction (auto-normalized to sum=1).
            perm_mean_md: geometric mean perm for this facies (mD).
                          Typical: shale 0.01–1, siltstone 1–50, sandstone 50–5000.
            perm_std_log: std of ln(k) within facies.
                          0.3 = tight distribution, 0.8 = typical, 1.5 = spread.
            poro_mean:    mean porosity for this facies.
        poro_std:         std of porosity, shared across all facies. Typical: 0.02–0.05.
        correlation_length: spatial scale of facies bodies as fraction of domain.
                          0.15 = small patches, 0.25–0.35 = realistic bodies.
        seed:             integer seed for reproducibility.

    Returns:
        perm: (nz, ny, nx) float64, m²
        poro: (nz, ny, nx) float64, dimensionless, clamped to [0.03, 0.45]
    """
    rng = np.random.default_rng(seed)

    weights = np.array([f['weight'] for f in facies], dtype=float)
    weights /= weights.sum()

    # Thresholds in N(0,1) space from cumulative facies proportions
    thresholds = norm.ppf(np.cumsum(weights[:-1]))

    indicator = gaussian_correlated_field(nx, ny, correlation_length, seed=seed)

    # Assign facies index: facies 0 occupies the lowest indicator values
    facies_map = np.zeros((ny, nx), dtype=int)
    for k, t in enumerate(thresholds):
        facies_map[indicator >= t] = k + 1

    perm_2d = np.empty((ny, nx), dtype=np.float64)
    poro_2d = np.empty((ny, nx), dtype=np.float64)

    for i, f in enumerate(facies):
        mask = facies_map == i
        n = int(mask.sum())
        if n == 0:
            continue
        rng_i = np.random.default_rng(int(rng.integers(0, 2**31)))
        z_k = rng_i.standard_normal(n)
        z_p = rng_i.standard_normal(n)
        ln_k_mean = np.log(f['perm_mean_md'] * MD_TO_M2)
        perm_2d[mask] = np.exp(ln_k_mean + f['perm_std_log'] * z_k)
        poro_2d[mask] = np.clip(f['poro_mean'] + poro_std * z_p, 0.03, 0.45)

    perm = np.broadcast_to(perm_2d[np.newaxis], (nz, ny, nx)).copy()
    poro = np.broadcast_to(poro_2d[np.newaxis], (nz, ny, nx)).copy()
    return perm, poro
